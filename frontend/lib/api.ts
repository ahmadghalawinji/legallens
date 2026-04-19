import type { ApiEnvelope, AnalysisResult, TaskResponse } from "./types";

const BASE = "/api/v1";

export async function uploadContract(
  file: File
): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}/contracts/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Upload failed: ${res.status}`);
  }

  const envelope: ApiEnvelope<{ task_id: string; message: string }> =
    await res.json();
  if (!envelope.data?.task_id) throw new Error("No task_id in response");
  return { task_id: envelope.data.task_id };
}

export async function getTaskStatus(taskId: string): Promise<TaskResponse> {
  const res = await fetch(`${BASE}/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Task fetch failed: ${res.status}`);
  const envelope: ApiEnvelope<TaskResponse> = await res.json();
  if (!envelope.data) throw new Error("Empty task response");
  return envelope.data;
}

export async function pollUntilComplete(
  taskId: string,
  onProgress: (progress: number, status: string) => void,
  intervalMs = 1500
): Promise<AnalysisResult> {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const task = await getTaskStatus(taskId);
        onProgress(task.progress, task.status);

        if (task.status === "completed" && task.result) {
          resolve(task.result);
        } else if (task.status === "failed") {
          reject(new Error(task.error ?? "Analysis failed"));
        } else {
          setTimeout(tick, intervalMs);
        }
      } catch (err) {
        reject(err);
      }
    };
    tick();
  });
}
