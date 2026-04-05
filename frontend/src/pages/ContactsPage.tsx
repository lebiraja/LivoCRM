import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Search,
  Trash2,
  Edit2,
  Mail,
  Phone,
  Building2,
  X,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

// Mock contacts for demo — all fields must match the Contact type
const MOCK_CONTACTS: Contact[] = [
  { id: "c1", name: "Sarah Johnson",  email: "sarah@acme.com",    phone: "+1 555-0101", company: "Acme Corp",           tags: ["enterprise", "hot-lead"], lead_score: 92, notes: "Interested in enterprise license",  created_at: "2024-01-15T10:00:00Z", updated_at: "2024-03-20T14:30:00Z" },
  { id: "c2", name: "Mike Chen",      email: "mike@globaltech.io", phone: "+1 555-0102", company: "GlobalTech",          tags: ["api", "integration"],      lead_score: 78, notes: "Wants API integration",            created_at: "2024-02-10T09:00:00Z", updated_at: "2024-03-18T11:00:00Z" },
  { id: "c3", name: "Lisa Park",      email: "lisa@startupxyz.co", phone: "+1 555-0103", company: "StartupXYZ",          tags: ["startup", "demo"],          lead_score: 65, notes: null,                              created_at: "2024-02-20T15:00:00Z", updated_at: "2024-03-15T09:00:00Z" },
  { id: "c4", name: "James Wilson",   email: "james@bigcorp.com",  phone: "+1 555-0104", company: "BigCorp Industries",  tags: ["enterprise"],               lead_score: 85, notes: "Budget approved for Q2",          created_at: "2024-01-05T08:00:00Z", updated_at: "2024-03-22T16:00:00Z" },
  { id: "c5", name: "Emma Davis",     email: "emma@dataflow.dev",  phone: "+1 555-0105", company: "DataFlow Inc",        tags: ["data", "pipeline"],         lead_score: 71, notes: "Needs data pipeline solution",    created_at: "2024-03-01T12:00:00Z", updated_at: "2024-03-21T10:00:00Z" },
  { id: "c6", name: "Alex Rivera",    email: "alex@mediaco.tv",    phone: "+1 555-0106", company: "MediaCo",             tags: ["media", "growth"],          lead_score: 58, notes: null,                              created_at: "2024-03-05T14:00:00Z", updated_at: "2024-03-19T13:00:00Z" },
  { id: "c7", name: "Priya Sharma",   email: "priya@finserv.com",  phone: "+1 555-0107", company: "FinServ Solutions",   tags: ["finance", "hot-lead"],      lead_score: 88, notes: "Ready to close by month end",    created_at: "2024-02-14T11:00:00Z", updated_at: "2024-03-23T15:00:00Z" },
  { id: "c8", name: "David Kim",      email: "david@healthtec.io", phone: "+1 555-0108", company: "HealthTec",           tags: ["healthcare", "compliance"], lead_score: 45, notes: "Compliance requirements pending", created_at: "2024-03-10T10:00:00Z", updated_at: "2024-03-20T12:00:00Z" },
];

function getScoreColor(score: number) {
  if (score >= 80) return "text-emerald-500";
  if (score >= 60) return "text-amber-500";
  return "text-rose-500";
}

/** Derive two-letter initials from a full name string */
function initials(name: string) {
  const parts = name.trim().split(" ");
  if (parts.length === 1) return parts[0][0] ?? "?";
  return (parts[0][0] ?? "") + (parts[parts.length - 1][0] ?? "");
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

export default function ContactsPage() {
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
      // API returns Contact[] (not paginated); we do client-side pagination
      const all = await contactsApi.list({ search });
      const filtered = search
        ? all.filter((c) =>
            `${c.name} ${c.email ?? ""} ${c.company ?? ""}`.toLowerCase().includes(search.toLowerCase())
          )
        : all;
      const start = (page - 1) * PAGE_SIZE;
      setContacts(filtered.slice(start, start + PAGE_SIZE));
      setTotalPages(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
    } catch {
      // Demo fallback
      const filtered = search
        ? MOCK_CONTACTS.filter((c) =>
            `${c.name} ${c.email ?? ""} ${c.company ?? ""}`.toLowerCase().includes(search.toLowerCase())
          )
        : MOCK_CONTACTS;
      const start = (page - 1) * PAGE_SIZE;
      setContacts(filtered.slice(start, start + PAGE_SIZE));
      setTotalPages(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
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
    } catch {
      // In demo mode, just close
      setDialogOpen(false);
    }
  };

  const handleDelete = async () => {
    try {
      await contactsApi.bulkDelete(Array.from(selected));
    } catch {
      // Demo fallback — remove from local state
      setContacts((prev) => prev.filter((c) => !selected.has(c.id)));
    }
    setSelected(new Set());
    setDeleteDialogOpen(false);
    loadContacts();
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
    } catch {
      setAiSummary(
        "Sarah Johnson is a high-priority lead at Acme Corp (VP of Engineering). She's shown strong intent through 3 demo calls. Recommended action: schedule final pricing discussion."
      );
    } finally {
      setAiLoading(false);
    }
  };

  const updateField = (key: keyof ContactCreate, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contacts</h1>
          <p className="text-sm text-muted-foreground">
            Manage your contacts and leads
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete ({selected.size})
            </Button>
          )}
          <Button size="sm" onClick={openNewDialog}>
            <Plus className="mr-2 h-4 w-4" />
            Add Contact
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search contacts…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="h-9 bg-muted/30 pl-9"
        />
      </div>

      {/* Contact List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : contacts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">No contacts found</p>
            <Button variant="outline" className="mt-4" onClick={openNewDialog}>
              <Plus className="mr-2 h-4 w-4" />
              Add your first contact
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {contacts.map((contact) => (
              <motion.div
                key={contact.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
              >
                <Card
                  className={cn(
                    "group cursor-pointer border-border/50 transition-all hover:border-border",
                    selected.has(contact.id) && "border-primary/50 bg-primary/5"
                  )}
                >
                  <CardContent className="flex items-center gap-4 p-4">
                    {/* Checkbox */}
                    <input
                      type="checkbox"
                      checked={selected.has(contact.id)}
                      onChange={() => toggleSelect(contact.id)}
                      className="h-4 w-4 shrink-0 rounded border-border accent-primary"
                    />

                    {/* Avatar */}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary uppercase">
                      {initials(contact.name)}
                    </div>

                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-medium">
                          {contact.name}
                        </p>
                        {contact.tags?.map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-[10px]"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                        {contact.company && (
                          <span className="flex items-center gap-1">
                            <Building2 className="h-3 w-3" />
                            {contact.company}
                          </span>
                        )}
                        {contact.email && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {contact.email}
                          </span>
                        )}
                        {contact.phone && (
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {contact.phone}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Score */}
                    <div className="text-right">
                      <p
                        className={cn(
                          "text-lg font-bold font-mono",
                          getScoreColor(contact.lead_score ?? 0)
                        )}
                      >
                        {contact.lead_score ?? "–"}
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        Lead Score
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={(e) => {
                          e.stopPropagation();
                          getAISummary();
                        }}
                      >
                        <Sparkles className="h-4 w-4 text-primary" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditDialog(contact);
                        }}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="flex items-center px-3 text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* AI Summary Popup */}
      <AnimatePresence>
        {(aiSummary || aiLoading) && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-6 right-6 z-50 max-w-sm"
          >
            <Card className="border-primary/30 bg-card/95 backdrop-blur-md">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Sparkles className="h-4 w-4 text-primary" />
                    AI Insight
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => {
                      setAiSummary(null);
                      setAiLoading(false);
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {aiLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-5/6" />
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {aiSummary}
                  </p>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingContact ? "Edit Contact" : "Add Contact"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={form.name}
                onChange={(e) => updateField("name", e.target.value)}
                placeholder="Full name"
                className="bg-muted/30"
              />
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={form.email ?? ""}
                onChange={(e) => updateField("email", e.target.value)}
                className="bg-muted/30"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={form.phone ?? ""}
                  onChange={(e) => updateField("phone", e.target.value)}
                  className="bg-muted/30"
                />
              </div>
              <div className="space-y-2">
                <Label>Company</Label>
                <Input
                  value={form.company ?? ""}
                  onChange={(e) => updateField("company", e.target.value)}
                  className="bg-muted/30"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Tags</Label>
              <div className="flex flex-wrap gap-1.5">
                {(form.tags || []).map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => removeTag(tag)}
                  >
                    {tag}
                    <X className="ml-1 h-3 w-3" />
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTag())}
                  placeholder="Add tag…"
                  className="bg-muted/30"
                />
                <Button variant="outline" size="sm" onClick={addTag}>
                  Add
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <textarea
                value={form.notes ?? ""}
                onChange={(e) => updateField("notes", e.target.value)}
                rows={3}
                className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave}>
                {editingContact ? "Save Changes" : "Create Contact"}
              </Button>
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
              This will permanently delete {selected.size} contact(s). This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </motion.div>
  );
}
