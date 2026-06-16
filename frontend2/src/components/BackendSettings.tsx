import { useEffect, useState } from "react";
import { checkHealth, getBackendUrl, setBackendUrl } from "@/lib/netsol-api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Settings2 } from "lucide-react";

interface Props {
  onSaved?: () => void;
}

export function BackendSettings({ onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "fail">("idle");

  useEffect(() => {
    if (open) setUrl(getBackendUrl());
  }, [open]);

  const test = async () => {
    setBackendUrl(url.trim());
    setStatus("checking");
    setStatus((await checkHealth()) ? "ok" : "fail");
  };

  const save = () => {
    setBackendUrl(url.trim());
    onSaved?.();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="glassOutline" size="sm">
          <Settings2 className="size-4" />
          Backend
        </Button>
      </DialogTrigger>
      <DialogContent className="glass-strong">
        <DialogHeader>
          <DialogTitle>Backend connection</DialogTitle>
          <DialogDescription>
            Enter the URL of your FastAPI RAG backend. Leave empty to use the same origin
            (e.g. a Vite proxy to <code>/api</code> and <code>/health</code>).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="backend-url">Backend URL</Label>
          <Input
            id="backend-url"
            placeholder="http://127.0.0.1:8000"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          {status === "ok" && (
            <p className="text-sm text-primary">✓ Connected — /health returned ok</p>
          )}
          {status === "fail" && (
            <p className="text-sm text-destructive">✗ Could not reach /health at that URL</p>
          )}
          {status === "checking" && (
            <p className="text-sm text-muted-foreground">Checking…</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="glassOutline" onClick={test}>
            Test connection
          </Button>
          <Button variant="brand" onClick={save}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
