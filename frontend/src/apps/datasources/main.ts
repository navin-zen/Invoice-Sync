export function DataSources() {
  console.log("Welcome to Data sources");
}

// @ts-expect-error does not exist on type 'Window & typeof globalThis'
window.DataSources = DataSources;
