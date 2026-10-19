// Build an analysis snapshot of every embedded JS module without executing it.
// All modules are roots: workers and computed dynamic imports must not disappear.
const fs = require('node:fs');
const esbuild = require('esbuild');

async function main() {
  const modules = JSON.parse(fs.readFileSync(0, 'utf8'));
  const names = Object.keys(modules).sort();
  if (!names.length) throw new Error('No JavaScript modules in Bun graph');
  const result = await esbuild.build({
    stdin: {contents: names.map((name, index) =>
      `export * as embeddedModule${index} from ${JSON.stringify(name)};`).join('\n')},
    bundle: true,
    write: false,
    platform: 'node',
    format: 'esm',
    target: 'esnext',
    treeShaking: false,
    ignoreAnnotations: true,
    minify: false,
    charset: 'utf8',
    logLevel: 'silent',
    metafile: true,
    plugins: [{
      name: 'embedded-source',
      setup(build) {
        build.onResolve({filter: /.*/}, args => {
          if (Object.hasOwn(modules, args.path)) {
            return {path: args.path, namespace: 'embedded'};
          }
          // Native libraries and non-JS assets remain explicit external imports.
          if (args.path.startsWith('/$bunfs/') && /(?:chunk-.*\.js|\/cli)$/.test(args.path)) {
            throw new Error(`Missing embedded JavaScript module: ${args.path}`);
          }
          return {path: args.path, external: true};
        });
        build.onLoad({filter: /.*/, namespace: 'embedded'}, args => ({
          contents: modules[args.path], loader: 'js',
        }));
      },
    }],
  });
  const count = Object.keys(result.metafile.inputs).filter(name => name.startsWith('embedded:')).length;
  if (count !== names.length) throw new Error(`Bundled ${count}/${names.length} modules`);
  process.stdout.write(`// Analysis snapshot: ${count} embedded Bun modules, esbuild ${esbuild.version}.\n`);
  process.stdout.write('// Modules are combined for inspection; this is not the original executable.\n');
  process.stdout.write(result.outputFiles[0].text);
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
