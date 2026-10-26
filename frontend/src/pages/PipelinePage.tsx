import { useCallback, useEffect, useState, type DragEvent } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { dealsApi } from "@/api/deals";
import type { Deal, DealCreate, DealStage } from "@/types";
import { cn } from "@/lib/utils";
import { formatINR } from "@/lib/format";
import { notifyApiError } from "@/lib/notifyError";

// Static pipeline stages – the API has no stages endpoint
const STAGE_DEFS: { id: DealStage; label: string }[] = [
  { id: "lead", label: "Lead" },
  { id: "qualified", label: "Qualified" },
  { id: "proposal", label: "Proposal" },
  { id: "negotiation", label: "Negotiation" },
  { id: "closed_won", label: "Closed ✓" },
  { id: "closed_lost", label: "Closed ✗" },
];

const EMPTY_FORM: DealCreate = {
  title: "",
  value: 0,
  stage: "lead",
  contact_id: "",
  notes: "",
};

export function PipelinePage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<DealStage | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [form, setForm] = useState<DealCreate>({ ...EMPTY_FORM });

  const loadData = useCallback(async () => {
    try {
      const response = await dealsApi.list();
      setDeals(response.items);
      setLoadError(false);
    } catch (error) {
      setLoadError(true);
      notifyApiError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const getDealsForStage = (stage: DealStage) => deals.filter((d) => d.stage === stage);

  const getStageTotal = (stage: DealStage) =>
    getDealsForStage(stage).reduce((sum, d) => sum + d.value, 0);

  // Used by both drag-and-drop and the per-card "Move to" select (keyboard and touch)
  const moveDeal = async (dealId: string, stage: DealStage) => {
    const deal = deals.find((d) => d.id === dealId);
    if (!deal || deal.stage === stage) return;

    const previous = deal.stage;
    const label = STAGE_DEFS.find((s) => s.id === stage)?.label ?? stage;
    setDeals((prev) => prev.map((d) => (d.id === dealId ? { ...d, stage } : d)));
    setAnnouncement(`${deal.title} moved to ${label}`);

    try {
      await dealsApi.moveStage(dealId, stage);
    } catch (error) {
      // Roll back to the stage the deal was in before the failed move
      setDeals((prev) => prev.map((d) => (d.id === dealId ? { ...d, stage: previous } : d)));
      setAnnouncement(`${deal.title} could not be moved`);
      notifyApiError(error);
    }
  };

  // ── Drag & Drop ──────────────────────────────────────────────────────────
  const handleDragStart = (dealId: string) => setDraggedId(dealId);
  const handleDragEnd = () => {
    setDraggedId(null);
    setDragOverStage(null);
  };

  const handleDragOver = (e: DragEvent, stage: DealStage) => {
    e.preventDefault();
    setDragOverStage(stage);
  };

  const handleDrop = (stage: DealStage) => {
    if (draggedId) void moveDeal(draggedId, stage);
    setDraggedId(null);
    setDragOverStage(null);
  };

  // ── Create Deal ───────────────────────────────────────────────────────────
  const handleCreateDeal = async () => {
    // Clean the payload — send null for empty contact_id (not empty string)
    const payload = {
      ...form,
      contact_id: form.contact_id?.trim() || undefined,
    };
    try {
      const created = await dealsApi.create(payload);
      setDeals((prev) => [...prev, created]);
    } catch (error) {
      notifyApiError(error);
      return; // Don't close dialog on failure
    }
    setDialogOpen(false);
    setForm({ ...EMPTY_FORM });
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <section aria-labelledby="pipeline-heading" className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 id="pipeline-heading" className="font-serif text-4xl leading-tight">
            Pipeline
          </h1>
          <p className="text-sm text-muted-foreground">Drag a deal, or use its Move to menu</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus aria-hidden="true" />
          New Deal
        </Button>
      </header>

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {loading ? (
        <div className="flex gap-3 overflow-hidden" aria-hidden="true">
          {[0, 1, 2].map((item) => (
            <Skeleton key={item} className="h-72 w-64 shrink-0 rounded-none" />
          ))}
        </div>
      ) : loadError ? (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border border-destructive/40 p-4">
          <p className="min-w-0 text-sm">Deals could not be loaded.</p>
          <Button variant="outline" onClick={() => void loadData()}>
            Try again
          </Button>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STAGE_DEFS.map((stage) => {
            const stageDeals = getDealsForStage(stage.id);
            const total = getStageTotal(stage.id);
            const isOver = dragOverStage === stage.id;

            return (
              <div
                key={stage.id}
                className={cn(
                  "flex w-64 shrink-0 flex-col border-t-2 transition-colors",
                  isOver ? "border-primary" : "border-border"
                )}
                onDragOver={(e) => handleDragOver(e, stage.id)}
                onDrop={() => handleDrop(stage.id)}
                onDragLeave={() => setDragOverStage(null)}
              >
                <div className="flex items-baseline justify-between gap-2 py-3">
                  <h2 className="min-w-0 break-words text-sm font-semibold">
                    {stage.label}
                    <span className="ml-2 font-normal text-muted-foreground tabular-nums">{stageDeals.length}</span>
                  </h2>
                  <span className="shrink-0 text-xs font-medium text-muted-foreground tabular-nums">
                    {formatINR(total, { compact: true })}
                  </span>
                </div>

                <ul className="flex flex-1 flex-col gap-2">
                  {stageDeals.map((deal) => (
                    <li
                      key={deal.id}
                      draggable
                      onDragStart={() => handleDragStart(deal.id)}
                      onDragEnd={handleDragEnd}
                      className={cn(
                        "grid min-w-0 cursor-grab gap-2 border-b border-border py-3 active:cursor-grabbing",
                        draggedId === deal.id && "opacity-40"
                      )}
                    >
                      <p className="min-w-0 break-words text-sm font-medium leading-snug">{deal.title}</p>
                      <p className="text-sm tabular-nums text-foreground">{formatINR(deal.value)}</p>
                      <label className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        Move to
                        <select
                          aria-label={`Move ${deal.title} to stage`}
                          value={deal.stage}
                          onChange={(event) => void moveDeal(deal.id, event.target.value as DealStage)}
                          className="h-11 min-w-0 flex-1 rounded-md border border-input bg-background px-2 text-base text-foreground md:h-8 md:text-sm"
                        >
                          {STAGE_DEFS.map((option) => (
                            <option key={option.id} value={option.id}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    </li>
                  ))}

                  {stageDeals.length === 0 && (
                    <li className="py-6 text-xs text-muted-foreground">Drop deals here</li>
                  )}
                </ul>
              </div>
            );
          })}
        </div>
      )}

      {/* New Deal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Deal</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="deal-title">Deal Title</Label>
              <Input
                id="deal-title"
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                placeholder="Enterprise License"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="deal-value">Value (₹)</Label>
                <Input
                  id="deal-value"
                  type="number"
                  inputMode="numeric"
                  value={form.value || ""}
                  onChange={(e) => setForm((prev) => ({ ...prev, value: Number(e.target.value) }))}
                  placeholder="50000"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deal-stage">Stage</Label>
                <select
                  id="deal-stage"
                  value={form.stage}
                  onChange={(e) => setForm((prev) => ({ ...prev, stage: e.target.value as DealStage }))}
                  className="h-11 w-full rounded-md border border-input bg-background px-3 text-base md:h-9 md:text-sm"
                >
                  {STAGE_DEFS.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="deal-notes">Notes</Label>
              <Textarea
                id="deal-notes"
                value={form.notes ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))}
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateDeal} disabled={!form.title}>
                Create Deal
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
