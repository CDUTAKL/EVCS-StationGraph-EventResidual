# Thesis storage archive, 2026-11-11

This is a storage snapshot, not a finalized thesis publication or an experimental result endorsement. Main-branch source work may remain uncommitted. The official Word/PDF are preserved as found; the separately named reordered candidate is the current editable draft.

`history.zip` stores content-addressed original byte pieces for 15 historical cache files. `manifest.json` lists the exact ordered pieces, sizes and SHA-256 of every original. All original hashes were reconstructed successfully before cleanup.

Restore into a new directory, never over a current file:

```sh
python3 -B scripts/archive_thesis_cache.py restore --archive-dir outputs/archives/thesis-cache-20261111 --restore-root /tmp/evcs-thesis-history-restored
```

After a fresh clone, fetch the archive through Git LFS before verification/restoration. `remote-verification.json` is written only after an independent remote download matches the archive hash. The local archive must remain available while historical cache copies are removed.
