import { useState } from "react";
import { motion } from "framer-motion";
import {
  User,
  Bell,
  Palette,
  Shield,
  Mail,
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
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";

type Tab = "profile" | "notifications" | "appearance" | "security";

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "security", label: "Security", icon: Shield },
];

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [notifications, setNotifications] = useState({
    email_deals: true,
    email_contacts: false,
    email_digest: true,
    push_deals: true,
    push_tasks: true,
  });

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
                    Profile editing is not available yet
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="profile-name">Full name</Label>
                    <Input
                      id="profile-name"
                      value={user?.full_name ?? ""}
                      readOnly
                      className="bg-muted/30"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-email">Email</Label>
                    <Input
                      id="profile-email"
                      value={user?.email ?? ""}
                      readOnly
                      className="bg-muted/30"
                    />
                  </div>
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
                    Notifications are not available yet
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
                            disabled
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
                            disabled
                            className="h-4 w-4 accent-primary"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
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
                    Password change is not available yet
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Current Password</Label>
                    <Input type="password" disabled className="bg-muted/30" />
                  </div>
                  <div className="space-y-2">
                    <Label>New Password</Label>
                    <Input type="password" disabled className="bg-muted/30" />
                  </div>
                  <div className="space-y-2">
                    <Label>Confirm New Password</Label>
                    <Input type="password" disabled className="bg-muted/30" />
                  </div>
                  <Button disabled>
                    <Shield className="mr-2 h-4 w-4" />
                    Update Password
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
