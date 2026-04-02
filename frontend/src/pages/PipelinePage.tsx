import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Plus,
  DollarSign,
  GripVertical,
  User,
} from "lucide-react";


import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { dealsApi } from "@/api/deals";
import type { Deal, DealCreate, DealStage } from "@/types";
import { cn } from "@/lib/utils";

// Static pipeline stages – the API has no stages endpoint
const STAGE_DEFS: { id: DealStage; label: string; color: string }[] = [
  { id: "lead",        label: "Lead",        color: "#6366F1" },
  { id: "qualified",  label: "Qualified",   color: "#06B6D4" },
  { id: "proposal",   label: "Proposal",    color: "#10B981" },
  { id: "negotiation",label: "Negotiation", color: "#F59E0B" },
  { id: "closed_won", label: "Closed ✓",   color: "#22C55E" },
  { id: "closed_lost",label: "Closed ✗",   color: "#EF4444" },
];

// Fallback mock data (shown when the API is unavailable / unauthenticated)
const MOCK_DEALS: Deal[] = [
  {
    id: "1", title: "Enterprise License", value: 120000,
    stage: "proposal", status: "active",
    contact_id: "c1", notes: "SOW sent",
    created_at: "2024-02-01T10:00:00Z", updated_at: "2024-03-20T14:00:00Z",
  },
  {
    id: "2", title: "API Integration", value: 85000,
    stage: "qualified", status: "active",
    contact_id: "c2", notes: "",
    created_at: "2024-02-15T09:00:00Z", updated_at: "2024-03-18T11:00:00Z",
  },
  {
    id: "3", title: "Startup Plan", value: 24000,
    stage: "lead", status: "active",
    contact_id: "c3", notes: "",
    created_at: "2024-03-01T15:00:00Z", updated_at: "2024-03-15T09:00:00Z",
  },
  {
    id: "4", title: "Data Pipeline", value: 95000,
    stage: "negotiation", status: "active",
    contact_id: "c4", notes: "Final pricing",
    created_at: "2024-01-20T08:00:00Z", updated_at: "2024-03-22T16:00:00Z",
  },
  {
    id: "5", title: "Annual Contract", value: 200000,
    stage: "closed_won", status: "won",
    contact_id: "c5", notes: "Awaiting signature",
    created_at: "2024-01-10T12:00:00Z", updated_at: "2024-03-23T15:00:00Z",
  },
  {
    id: "6", title: "Pilot Program", value: 15000,
    stage: "lead", status: "active",
    contact_id: "c6", notes: "",
    created_at: "2024-03-10T14:00:00Z", updated_at: "2024-03-19T13:00:00Z",
  },
];

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

const EMPTY_FORM: DealCreate = {
  title: "",
  value: 0,
  stage: "lead",
  contact_id: "",
  notes: "",
};

export default function PipelinePage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<DealStage | null>(null);
  const [form, setForm] = useState<DealCreate>({ ...EMPTY_FORM });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await dealsApi.list();
      setDeals(data);
    } catch {
      setDeals(MOCK_DEALS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const getDealsForStage = (stage: DealStage) =>
    deals.filter((d) => d.stage === stage);

  const getStageTotal = (stage: DealStage) =>
    getDealsForStage(stage).reduce((sum, d) => sum + d.value, 0);

  // ── Drag & Drop ──────────────────────────────────────────────────────────
  const handleDragStart = (dealId: string) => setDraggedId(dealId);
  const handleDragEnd = () => { setDraggedId(null); setDragOverStage(null); };

  const handleDragOver = (e: React.DragEvent, stage: DealStage) => {
    e.preventDefault();
    setDragOverStage(stage);
  };

  const handleDrop = async (stage: DealStage) => {
    if (!draggedId) return;
    try {
      await dealsApi.moveStage(draggedId, stage);
    } catch {
      // Demo fallback – update locally
    }
    setDeals((prev) =>
      prev.map((d) => d.id === draggedId ? { ...d, stage } : d)
    );
    setDraggedId(null);
    setDragOverStage(null);
  };

  // ── Create Deal ───────────────────────────────────────────────────────────
  const handleCreateDeal = async () => {
    try {
      const created = await dealsApi.create(form);
      setDeals((prev) => [...prev, created]);
    } catch {
      // Demo fallback
      const newDeal: Deal = {
        id: crypto.randomUUID(),
        title: form.title,
        value: form.value,
        stage: form.stage,
        status: "active",
        contact_id: form.contact_id ?? "",
        notes: form.notes ?? null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setDeals((prev) => [...prev, newDeal]);
    }
    setDialogOpen(false);
    setForm({ ...EMPTY_FORM });
  };

  // ── Render ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-4 overflow-x-auto">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-96 w-64 shrink-0 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pipeline</h1>
          <p className="text-sm text-muted-foreground">
            Drag deals between stages to update progress
          </p>
        </div>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Deal
        </Button>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGE_DEFS.map((stage) => {
          const stageDeals = getDealsForStage(stage.id);
          const total = getStageTotal(stage.id);
          const isOver = dragOverStage === stage.id;

          return (
            <div
              key={stage.id}
              className={cn(
                "flex w-64 shrink-0 flex-col rounded-xl border transition-all",
                isOver
                  ? "border-primary/50 bg-primary/5"
                  : "border-border/50 bg-muted/20"
              )}
              onDragOver={(e) => handleDragOver(e, stage.id)}
              onDrop={() => handleDrop(stage.id)}
              onDragLeave={() => setDragOverStage(null)}
            >
              {/* Stage Header */}
              <div className="flex items-center justify-between p-3 pb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: stage.color }}
                  />
                  <span className="text-sm font-semibold">{stage.label}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    {stageDeals.length}
                  </Badge>
                </div>
                <span className="text-xs font-medium text-muted-foreground">
                  {formatCurrency(total)}
                </span>
              </div>

              {/* Deals */}
              <div className="flex flex-1 flex-col gap-2 p-2 pt-0">
                {stageDeals.map((deal) => (
                  <motion.div
                    key={deal.id}
                    layout
                    draggable
                    onDragStart={() => handleDragStart(deal.id)}
                    onDragEnd={handleDragEnd}
                    className={cn(
                      "group cursor-grab rounded-lg border border-border/50 bg-card p-3 transition-all hover:border-border active:cursor-grabbing",
                      draggedId === deal.id && "opacity-40"
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-medium leading-tight">
                        {deal.title}
                      </p>
                      <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100" />
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <User className="h-3 w-3" />
                        <span className="truncate max-w-[80px]">
                          {deal.contact_id || "—"}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-xs font-semibold text-emerald-500">
                        <DollarSign className="h-3 w-3" />
                        {formatCurrency(deal.value)}
                      </div>
                    </div>
                  </motion.div>
                ))}

                {/* Empty state */}
                {stageDeals.length === 0 && (
                  <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-border/30 p-6">
                    <p className="text-xs text-muted-foreground">
                      Drop deals here
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* New Deal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Deal</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Deal Title</Label>
              <Input
                value={form.title}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, title: e.target.value }))
                }
                placeholder="Enterprise License"
                className="bg-muted/30"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Value ($)</Label>
                <Input
                  type="number"
                  value={form.value || ""}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      value: Number(e.target.value),
                    }))
                  }
                  placeholder="50000"
                  className="bg-muted/30"
                />
              </div>
              <div className="space-y-2">
                <Label>Stage</Label>
                <select
                  value={form.stage}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      stage: e.target.value as DealStage,
                    }))
                  }
                  className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
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
              <Label>Notes</Label>
              <textarea
                value={form.notes ?? ""}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, notes: e.target.value }))
                }
                rows={3}
                className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
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
    </motion.div>
  );
}
