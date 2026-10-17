// Draft JS surface of the sigma-resume engine (redesign P5, §19).
//
// resumeInWorker(request, {deadlineMs}) runs ONE resume request in a disposable
// worker thread over the wasm build of impl-rs/src/main.rs. If the deadline
// passes, the worker is terminated and the result is the LOCAL outcome
// {"outcome":"DEADLINE"}: no state, no answer. The caller keeps the checkpoint it
// already had; a timeout is never a receipt.
import { Worker } from "node:worker_threads";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const WASM = new URL("./target/wasm32-unknown-unknown/release/sigma_resume_wasm.wasm", import.meta.url);

export function runWasm(wasmBytes, requestText) {
  const e = new WebAssembly.Instance(new WebAssembly.Module(wasmBytes), {}).exports;
  const req = new TextEncoder().encode(requestText);
  const ptr = e.alloc(req.length);
  new Uint8Array(e.memory.buffer, ptr, req.length).set(req);
  e.resume(ptr, req.length);
  const out = new Uint8Array(e.memory.buffer, e.out_ptr(), e.out_len());
  return new TextDecoder().decode(out.slice());
}

export function resumeInWorker(request, { deadlineMs = 10_000 } = {}) {
  const source = `
    import { parentPort, workerData } from "node:worker_threads";
    import { runWasm } from ${JSON.stringify(import.meta.url)};
    parentPort.postMessage(runWasm(workerData.wasm, workerData.request));`;
  const wasm = readFileSync(fileURLToPath(WASM));
  return new Promise((resolve) => {
    const worker = new Worker(new URL("data:text/javascript," + encodeURIComponent(source)),
      { workerData: { wasm, request: typeof request === "string" ? request : JSON.stringify(request) } });
    const timer = setTimeout(() => { worker.terminate(); resolve({ outcome: "DEADLINE" }); }, deadlineMs);
    worker.once("message", (text) => { clearTimeout(timer); worker.terminate(); resolve(JSON.parse(text)); });
    worker.once("error", (err) => { clearTimeout(timer); resolve({ outcome: "RESOURCE_FAULT", detail: String(err) }); });
  });
}

// CLI: node resume_worker.mjs [deadline-ms] < request.json
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const request = readFileSync(0, "utf8");
    const deadlineMs = Number(process.argv[2] ?? 10_000);
    const result = await resumeInWorker(request, { deadlineMs });
    console.log(JSON.stringify(result));
  } catch (error) {
    console.log(JSON.stringify({ outcome: "RESOURCE_FAULT", detail: String(error) }));
    process.exitCode = 1;
  }
}
