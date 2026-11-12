// The page engine's files by path, which vite.config.ts packs as the page builds
declare module 'virtual:engine' {
  const files: Record<string, string>
  export default files
}
