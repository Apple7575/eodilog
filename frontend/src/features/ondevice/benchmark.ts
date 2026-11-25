// Opt in at bundle build time, on a dedicated test album only.
export const benchmarkEnabled = process.env.EXPO_PUBLIC_ONDEVICE_BENCHMARK === '1';

export function benchmarkEvent(kind: string, fields: Record<string, unknown> = {}) {
  if (benchmarkEnabled)
    console.log(`ONDEV_BENCH ${JSON.stringify({ kind, atMs: Date.now(), ...fields })}`);
}
