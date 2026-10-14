# Third-party notices

Components committed to this repository in built form. Their licence texts are kept next to the files.

| Component | Version | Licence | Location | Licence file |
|---|---|---|---|---|
| Tabler (`@tabler/core`) | 1.6.0 | MIT | `apps/web/public/vendor/tabler/` | `apps/web/public/vendor/tabler/LICENSE` |
| Tabler Icons (outline glyph paths) | 3.35.0 | MIT | `apps/web/resources/views/components/icon.blade.php` | `apps/web/resources/icons/LICENSE` |
| DejaVu Sans (regular, bold) | 2.37 | Bitstream Vera licence + public-domain changes | `tools/synth/src/renova_synth/fonts/` | `tools/synth/src/renova_synth/fonts/LICENSE-DejaVu.txt` |
| Liberation Sans (regular, bold) | 2.1 | SIL Open Font License 1.1 | `tools/synth/src/renova_synth/fonts/` | `tools/synth/src/renova_synth/fonts/LICENSE-Liberation.txt` |

Package-manager dependencies (Composer, pip) keep their own licences and are not redistributed
in this repository. Container images used at runtime:

| Image | Licence | Note |
|---|---|---|
| `pgsty/minio`, `pgsty/mc` | AGPL-3.0 | Community build of MinIO, run as a separate unmodified service (ADR-0004). |
| `postgres`, `redis`, `php`, `python`, `composer` (official images) | PostgreSQL, RSALv2/SSPLv1 (Redis 7.4), PHP, PSF, MIT | Base/runtime images. |
