Synthetic documents copied from `make synth` (seed 2026): fictitious data, see tools/synth.

`ocr/` holds cloud OCR responses for the adapter parsers. They follow the documented response
schemas (Azure Document Intelligence `prebuilt-read` 2024-11-30, Google Document AI `process`
v1) for a short invoice header; they were written to those schemas, not recorded from a live
service, because the project has no cloud credentials. Replace them with recorded responses
when a benchmark run is made (phase 7).
