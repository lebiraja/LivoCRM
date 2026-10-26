import { useEffect, useState, useCallback } from "react";
import { Plus, Search, Trash2, Edit2, X, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
} from "@/components/ui/alert-dialog";
import { contactsApi } from "@/api/contacts";
import { analyticsApi } from "@/api/analytics";
import type { Contact, ContactCreate } from "@/types";
import { cn } from "@/lib/utils";
import { notifyApiError } from "@/lib/notifyError";

function getScoreColor(score: number) {
  if (score >= 80) return "text-success";
  if (score >= 60) return "text-warning";
  return "text-overdue";
}

const emptyForm: ContactCreate = {
  name: "",
  email: "",
  phone: "",
  company: "",
  tags: [],
  notes: "",
};

const PAGE_SIZE = 20;

export function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [form, setForm] = useState<ContactCreate>(emptyForm);
  const [tagInput, setTagInput] = useState("");
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const loadContacts = useCallback(async () => {
    setLoading(true);
    try {
      // API now returns paginated response: { total, items }
      const response = await contactsApi.list({ search, skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE });
      setContacts(response.items);
      setTotalPages(Math.max(1, Math.ceil(response.total / PAGE_SIZE)));
    } catch (error) {
      notifyApiError(error);
      setContacts([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [search, page]);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  const openNewDialog = () => {
    setEditingContact(null);
    setForm(emptyForm);
    setDialogOpen(true);
  };

  const openEditDialog = (contact: Contact) => {
    setEditingContact(contact);
    setForm({
      name: contact.name,
      email: contact.email ?? "",
      phone: contact.phone ?? "",
      company: contact.company ?? "",
      tags: contact.tags ?? [],
      notes: contact.notes ?? "",
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingContact) {
        await contactsApi.update(editingContact.id, form);
      } else {
        await contactsApi.create(form);
      }
      setDialogOpen(false);
      loadContacts();
    } catch (error) {
      notifyApiError(error);
    }
  };

  const handleDelete = async () => {
    try {
      await contactsApi.bulkDelete(Array.from(selected));
      setSelected(new Set());
      setDeleteDialogOpen(false);
      loadContacts();
    } catch (error) {
      notifyApiError(error);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const addTag = () => {
    if (tagInput.trim() && !(form.tags || []).includes(tagInput.trim())) {
      setForm((prev) => ({
        ...prev,
        tags: [...(prev.tags || []), tagInput.trim()],
      }));
      setTagInput("");
    }
  };

  const removeTag = (tag: string) => {
    setForm((prev) => ({
      ...prev,
      tags: (prev.tags || []).filter((t) => t !== tag),
    }));
  };

  /** Fetch AI insights and display the first insight as a "summary" for this contact */
  const getAISummary = async () => {
    setAiLoading(true);
    setAiSummary(null);
    try {
      const res = await analyticsApi.getInsights();
      setAiSummary(res.insights[0] ?? "No insights available.");
    } catch (error) {
      notifyApiError(error);
    } finally {
      setAiLoading(false);
    }
  };

  const updateField = (key: keyof ContactCreate, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <section aria-labelledby="contacts-heading" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 id="contacts-heading" className="font-serif text-4xl leading-tight">
            Contacts
          </h1>
          <p className="text-sm text-muted-foreground">Manage your contacts and leads</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {selected.size > 0 && (
            <Button variant="destructive" onClick={() => setDeleteDialogOpen(true)}>
              <Trash2 aria-hidden="true" />
              Delete ({selected.size})
            </Button>
          )}
          <Button onClick={openNewDialog}>
            <Plus aria-hidden="true" />
            Add Contact
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search aria-hidden="true" className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          aria-label="Search contacts"
          placeholder="Search contacts…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="h-11 pl-9 md:h-9"
        />
      </div>

      {/* Contact List */}
      {loading ? (
        <div className="space-y-px" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20 w-full rounded-none" />
          ))}
        </div>
      ) : contacts.length === 0 ? (
        <div className="space-y-3 border-y border-border py-10">
          <p className="text-muted-foreground">No contacts found</p>
          <Button variant="outline" onClick={openNewDialog}>
            <Plus aria-hidden="true" />
            Add your first contact
          </Button>
        </div>
      ) : (
        <ul className="border-t border-border">
          {contacts.map((contact) => {
            const details = [contact.company, contact.email, contact.phone].filter(Boolean).join(" · ");
            return (
              <li
                key={contact.id}
                className={cn(
                  "flex min-w-0 items-start gap-3 border-b border-border py-4",
                  selected.has(contact.id) && "bg-muted/60"
                )}
              >
                <input
                  type="checkbox"
                  aria-label={`Select ${contact.name}`}
                  checked={selected.has(contact.id)}
                  onChange={() => toggleSelect(contact.id)}
                  className="mt-1 size-5 shrink-0 accent-primary"
                />

                <div className="min-w-0 flex-1 space-y-1">
                  <p className="min-w-0 break-words text-base font-medium">{contact.name}</p>
                  {details && <p className="min-w-0 break-words text-sm text-muted-foreground">{details}</p>}
                  {contact.tags?.length > 0 && (
                    <p className="min-w-0 break-words text-xs text-muted-foreground">{contact.tags.join(" · ")}</p>
                  )}
                </div>

                <div className="shrink-0 text-right">
                  <p className={cn("font-serif text-2xl tabular-nums", getScoreColor(contact.lead_score ?? 0))}>
                    {contact.lead_score ?? "–"}
                  </p>
                  <p className="text-xs text-muted-foreground">Lead score</p>
                </div>

                <div className="flex shrink-0 gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-11 md:size-8"
                    aria-label={`Get AI insight for ${contact.name}`}
                    onClick={() => getAISummary()}
                  >
                    <Sparkles aria-hidden="true" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-11 md:size-8"
                    aria-label={`Edit ${contact.name}`}
                    onClick={() => openEditDialog(contact)}
                  >
                    <Edit2 aria-hidden="true" />
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav aria-label="Pagination" className="flex items-center justify-center gap-2">
          <Button variant="outline" size="icon" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft aria-hidden="true" />
          </Button>
          <span className="px-3 text-sm text-muted-foreground tabular-nums">
            Page {page} of {totalPages}
          </span>
          <Button variant="outline" size="icon" aria-label="Next page" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            <ChevronRight aria-hidden="true" />
          </Button>
        </nav>
      )}

      {/* AI Summary Popup */}
      {(aiSummary || aiLoading) && (
        <aside
          aria-label="AI insight"
          className="fixed right-4 bottom-20 z-50 w-[min(24rem,calc(100vw-2rem))] border border-border bg-popover p-4 text-popover-foreground shadow-[0_4px_16px_rgb(0_0_0/0.10)] md:right-6 md:bottom-6"
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <span className="rounded-sm border border-border px-1.5 text-xs font-medium text-muted-foreground">AI</span>
              Insight
            </p>
            <Button
              variant="ghost"
              size="icon"
              className="size-9"
              aria-label="Close AI insight"
              onClick={() => {
                setAiSummary(null);
                setAiLoading(false);
              }}
            >
              <X aria-hidden="true" />
            </Button>
          </div>
          {aiLoading ? (
            <div className="space-y-2" role="status">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : (
            <p className="text-sm leading-relaxed break-words text-muted-foreground">{aiSummary}</p>
          )}
        </aside>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingContact ? "Edit Contact" : "Add Contact"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="contact-name">Name</Label>
              <Input
                id="contact-name"
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="Full name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact-email">Email</Label>
              <Input
                id="contact-email"
                type="email"
                autoComplete="email"
                value={form.email ?? ""}
                onChange={(e) => updateField("email", e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="contact-phone">Phone</Label>
                <Input
                  id="contact-phone"
                  type="tel"
                  autoComplete="tel"
                  value={form.phone ?? ""}
                  onChange={(e) => updateField("phone", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact-company">Company</Label>
                <Input
                  id="contact-company"
                  value={form.company ?? ""}
                  onChange={(e) => updateField("company", e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact-tag">Tags</Label>
              <div className="flex flex-wrap gap-1.5">
                {(form.tags || []).map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => removeTag(tag)}
                    aria-label={`Remove tag ${tag}`}
                    className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs"
                  >
                    {tag}
                    <X aria-hidden="true" className="size-3" />
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  id="contact-tag"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
                  placeholder="Add tag…"
                />
                <Button variant="outline" onClick={addTag}>
                  Add
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact-notes">Notes</Label>
              <Textarea
                id="contact-notes"
                value={form.notes ?? ""}
                onChange={(e) => updateField("notes", e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave}>{editingContact ? "Save Changes" : "Create Contact"}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete contacts?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {selected.size} contact(s). This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-white hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
