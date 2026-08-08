# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project
doesn't follow SemVer yet since there are no releases.

## [Unreleased]

### Added
- Pluggable OCR pipeline: PDF → page images → OCR (Parinamika primary,
  Google Vision fallback, optional PaddleOCR) → cross-check diffing → LLM
  structuring pass into page-cited, commentary-layer-tagged JSON.
- Project architecture and research writeup (`docs/plan.md`).
- Phase 0 OCR feasibility test on two sample books
  (`docs/phase-0-findings.md`).
- Test suite for the pipeline's schema, cross-check, and rendering logic.
- Open-source project scaffolding: license, contributing guide, code of
  conduct, security policy, issue/PR templates, CI.
