import { useState } from "react";
import { motion } from "framer-motion";
import {
  User,
  Bell,
  Palette,
  Shield,
  Mail,
  Save,
  Moon,
  Sun,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Tab = "profile" | "notifications" | "appearance" | "security";

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "security", label: "Security", icon: Shield },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const [saved, setSaved] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [profile, setProfile] = useState({
    first_name: "Lebi",
    last_name: "Raja",
    email: "lebi@livocrm.com",
    company: "LivoCRM",
    timezone: "America/New_York",
  });
  const [notifications, setNotifications] = useState({
    email_deals: true,
    email_contacts: false,
    email_digest: true,
    push_deals: true,
    push_tasks: true,
  });

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggleTheme = (t: "light" | "dark") => {
    setTheme(t);
    document.documentElement.classList.toggle("dark", t === "dark");
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Sidebar */}
        <nav className="flex lg:w-52 lg:flex-col">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                  activeTab === tab.id
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 space-y-6">
          {activeTab === "profile" && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Profile Information</CardTitle>
                  <CardDescription>
                    Update your personal details
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">
                      {profile.first_name[0]}
                      {profile.last_name[0]}
                    </div>
                    <div>
                      <p className="font-medium">
                        {profile.first_name} {profile.last_name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {profile.email}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>First name</Label>
                      <Input
                        value={profile.first_name}
                        onChange={(e) =>
                          setProfile((p) => ({
                            ...p,
                            first_name: e.target.value,
                          }))
                        }
                        className="bg-muted/30"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Last name</Label>
                      <Input
                        value={profile.last_name}
                        onChange={(e) =>
                          setProfile((p) => ({
                            ...p,
                            last_name: e.target.value,
                          }))
                        }
                        className="bg-muted/30"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      value={profile.email}
                      onChange={(e) =>
                        setProfile((p) => ({ ...p, email: e.target.value }))
                      }
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Company</Label>
                      <Input
                        value={profile.company}
                        onChange={(e) =>
                          setProfile((p) => ({
                            ...p,
                            company: e.target.value,
                          }))
                        }
                        className="bg-muted/30"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Timezone</Label>
                      <select
                        value={profile.timezone}
                        onChange={(e) =>
                          setProfile((p) => ({
                            ...p,
                            timezone: e.target.value,
                          }))
                        }
                        className="w-full rounded-md border border-border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        <option value="America/New_York">Eastern Time</option>
                        <option value="America/Chicago">Central Time</option>
                        <option value="America/Denver">Mountain Time</option>
                        <option value="America/Los_Angeles">Pacific Time</option>
                        <option value="UTC">UTC</option>
                      </select>
                    </div>
                  </div>
                  <Button onClick={handleSave}>
                    <Save className="mr-2 h-4 w-4" />
                    {saved ? "Saved!" : "Save Changes"}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {activeTab === "notifications" && (
            <motion.div
              key="notifications"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Notification Preferences
                  </CardTitle>
                  <CardDescription>
                    Choose how you want to be notified
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
                      <Mail className="h-4 w-4" />
                      Email Notifications
                    </h3>
                    <div className="space-y-3">
                      {([
                        ["email_deals", "Deal updates", "When deals change stage or close"],
                        ["email_contacts", "New contacts", "When new contacts are added"],
                        ["email_digest", "Daily digest", "Daily summary of pipeline activity"],
                      ] as const).map(([key, label, desc]) => (
                        <label
                          key={key}
                          className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                        >
                          <div>
                            <p className="text-sm font-medium">{label}</p>
                            <p className="text-xs text-muted-foreground">
                              {desc}
                            </p>
                          </div>
                          <input
                            type="checkbox"
                            checked={notifications[key]}
                            onChange={() =>
                              setNotifications((n) => ({
                                ...n,
                                [key]: !n[key],
                              }))
                            }
                            className="h-4 w-4 accent-primary"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
                      <Bell className="h-4 w-4" />
                      Push Notifications
                    </h3>
                    <div className="space-y-3">
                      {([
                        ["push_deals", "Deal alerts", "Instant alerts for deal changes"],
                        ["push_tasks", "Task reminders", "Reminders for upcoming tasks"],
                      ] as const).map(([key, label, desc]) => (
                        <label
                          key={key}
                          className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                        >
                          <div>
                            <p className="text-sm font-medium">{label}</p>
                            <p className="text-xs text-muted-foreground">
                              {desc}
                            </p>
                          </div>
                          <input
                            type="checkbox"
                            checked={notifications[key]}
                            onChange={() =>
                              setNotifications((n) => ({
                                ...n,
                                [key]: !n[key],
                              }))
                            }
                            className="h-4 w-4 accent-primary"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                  <Button onClick={handleSave}>
                    <Save className="mr-2 h-4 w-4" />
                    {saved ? "Saved!" : "Save Preferences"}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {activeTab === "appearance" && (
            <motion.div
              key="appearance"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Appearance</CardTitle>
                  <CardDescription>
                    Customize the look and feel
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="mb-3 block">Theme</Label>
                    <div className="flex gap-3">
                      {([
                        { id: "light" as const, icon: Sun, label: "Light" },
                        { id: "dark" as const, icon: Moon, label: "Dark" },
                      ]).map(({ id, icon: Icon, label }) => (
                        <button
                          key={id}
                          onClick={() => toggleTheme(id)}
                          className={cn(
                            "flex items-center gap-2 rounded-lg border px-4 py-3 transition-all",
                            theme === id
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-border/50 text-muted-foreground hover:border-border"
                          )}
                        >
                          <Icon className="h-4 w-4" />
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label className="mb-3 block">Accent Color</Label>
                    <div className="flex gap-2">
                      {[
                        "#6366F1",
                        "#06B6D4",
                        "#10B981",
                        "#F59E0B",
                        "#F43F5E",
                        "#A855F7",
                      ].map((color) => (
                        <button
                          key={color}
                          className="h-8 w-8 rounded-full border-2 border-transparent transition-all hover:scale-110 hover:border-foreground/20"
                          style={{ backgroundColor: color }}
                          onClick={() => {
                            // In a real app, this would update CSS custom properties
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {activeTab === "security" && (
            <motion.div
              key="security"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-4"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Change Password</CardTitle>
                  <CardDescription>
                    Update your password regularly
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Current Password</Label>
                    <Input type="password" className="bg-muted/30" />
                  </div>
                  <div className="space-y-2">
                    <Label>New Password</Label>
                    <Input type="password" className="bg-muted/30" />
                  </div>
                  <div className="space-y-2">
                    <Label>Confirm New Password</Label>
                    <Input type="password" className="bg-muted/30" />
                  </div>
                  <Button onClick={handleSave}>
                    <Shield className="mr-2 h-4 w-4" />
                    Update Password
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Active Sessions</CardTitle>
                  <CardDescription>
                    Manage your active sessions
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between rounded-lg border border-border/50 p-3">
                    <div>
                      <p className="text-sm font-medium">Current Session</p>
                      <p className="text-xs text-muted-foreground">
                        Linux · Chrome · New York, US
                      </p>
                    </div>
                    <Badge className="bg-emerald/10 text-emerald">
                      Active
                    </Badge>
                  </div>
                  <Button variant="outline" size="sm" className="w-full">
                    Sign out all other sessions
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
