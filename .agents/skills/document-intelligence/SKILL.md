
---
name: document-intelligence
description: Defines secure document processing for AIC-Flow, including file validation, quarantine, PDF text extraction, RapidOCR with ONNX Runtime, structured field extraction, SHA-256, perceptual hashing, metadata observations, text-layer comparison, QR handling and digital signature checks. Use when implementing or reviewing document-related functionality.
---

# AIC-Flow Document Intelligence

## 1. Objective

Implement a secure and explainable document intelligence pipeline.

The purpose is to extract useful evidence from supporting documents, compare it with application declarations and authorised source records, and provide traceable observations for human review.

Document intelligence must never independently declare a document fraudulent or issue a regulatory decision.

The system should preserve:
- Original document bytes.
- Immutable document versions.
- Processing history.
- Extracted text and structured fields.
- Extraction confidence.
- Page and bounding-box locations.
- Integrity observations.
- Verification attempts.
- Evidence references.

## 2. Core Technology

Use the existing backend architecture:

- Python 3.13.
- FastAPI.
- Celery.
- Redis 7.2.x.
- PostgreSQL 18.
- SQLAlchemy 2.
- pypdf and pypdfium2 for PDF text extraction and bounded page rendering.
- RapidOCR with ONNX Runtime for scanned-document OCR.
- OpenCV for image preprocessing.
- Pillow for image handling.
- Do not claim digital-signature validation as implemented unless a trust-policy-aware verifier is present and tested; PyHanko is only a candidate if that capability is deliberately added.
- hashlib for SHA-256.
- A suitable perceptual hashing implementation for pHash.
- ClamAV for malware scanning.

Pin compatible dependencies.

Do not add unnecessary document-processing frameworks.

## 3. Document Processing Pipeline

Follow this order:

1. Request authorization.
2. Receive multipart file upload.
3. Place file in private quarantine.
4. Validate extension and actual file type.
5. Validate size, page count and image dimensions.
6. Perform malware scanning.
7. Calculate SHA-256.
8. Create an immutable document version.
9. Record metadata observations.
10. Extract existing PDF text where possible.
11. Apply OCR when required.
12. Extract structured fields.
13. Perform document-specific checks.
14. Perform separate signature and issuer verification checks where supported.
15. Store results and evidence references.
16. Route uncertain or suspicious cases for appropriate review.

Do not execute expensive OCR operations inside the upload HTTP request.

Use Celery workers.

The upload API should acknowledge receipt and return the document identifier and processing status.

## 4. Secure File Intake

Accept only the formats required by the prototype:

- PDF.
- JPEG.
- PNG.

Use a strict extension allowlist.

Never trust the filename extension alone.

Inspect:
- Filename extension.
- Declared content type.
- MIME detected from actual bytes.
- Magic bytes/file signature.
- File size.
- PDF page count.
- Image dimensions.
- File parsing result.

Use random private storage keys.

Never use an original filename directly as a filesystem path.

Never construct public file URLs.

Prevent:
- Path traversal.
- Malformed PDF uploads.
- Unsupported file formats.
- Unexpected oversized files.
- Unsafe image dimensions.
- Duplicate processing caused by repeated requests.

Set explicit configurable file-size and page-count limits.

Do not silently process unsupported documents.

## 5. Quarantine and Malware Scanning

New uploads must initially enter private quarantine.

The document must not become available for normal viewing or extraction until the required security checks have completed.

Use ClamAV for the prototype malware scan.

Record:
- Scanner name.
- Scanner version.
- Signature database version where available.
- Scan timestamp.
- Scan outcome.
- Processing failure details.

Possible outcomes:
- CLEAN.
- INFECTED.
- ERROR.
- UNAVAILABLE.

An unavailable scanner must not be represented as a successful clean scan.

Quarantined or infected files must not enter the ordinary processing pipeline.

Keep operational errors separate from sensitive document contents.

## 6. Immutable Document Versioning

Never overwrite uploaded original document bytes.

Maintain separate records for:

- Logical document.
- Document version.
- Uploaded file metadata.
- Processing job.
- Extracted text.
- Structured fields.

Every replacement creates a new document version.

Keep the relationship to the previous version.

Record:
- Document ID.
- Version ID.
- Version number.
- Original filename for display.
- Private storage key.
- Detected MIME type.
- Byte size.
- SHA-256.
- Upload timestamp.
- Uploading user.
- Previous version reference.

Do not store public storage URLs.

Never use a hash match as permission to delete an uploaded record.

An exact duplicate is an integrity observation, not automatically a reason to discard evidence.

## 7. SHA-256 Integrity

Use SHA-256 to calculate a digest of the exact uploaded file bytes.

Prefer streaming hashing for larger documents.

Store the digest with the document version.

When comparing two files:
- Equal SHA-256 indicates equal bytes with overwhelming practical confidence.
- Different SHA-256 indicates different bytes.
- Different bytes do not prove tampering or forgery.

Display the digest in the document details interface.

Preserve the original digest even when a new version is uploaded.

## 8. Metadata Observations

Extract available:
- PDF Info metadata.
- XMP metadata.
- EXIF metadata.
- Creation timestamps.
- Modification timestamps.
- Display filename.
- Available embedded file properties.

Treat all client-supplied metadata as untrusted observations.

Metadata timestamps are not official issuer timestamps.

Record missing or inconsistent metadata without automatically declaring manipulation.

Keep metadata observations separate from:
- SHA-256.
- Digital signature.
- Issuer verification.
- OCR output.

## 9. PDF Text Extraction

Always attempt PDF text-layer extraction before invoking OCR.

Use pypdf or another approved compatible text extractor.

Evaluate whether:
- A usable text layer exists.
- Sufficient text was extracted.
- The text contains expected readable information.
- The result is suitable for the required field extraction.

If the PDF contains a usable text layer, preserve the extracted text and page references.

If extraction is inadequate, use the OCR pipeline.

Do not assume every PDF is digitally generated or text-searchable.

Do not assume every scanned PDF lacks an embedded text layer.

## 10. OCR Pipeline

Use the existing RapidOCR with ONNX Runtime pipeline for scanned-document OCR.

The prototype must support representative English and Tamil test documents.

Recommended processing:

1. Render bounded PDF pages to images.
2. Preprocess images with OpenCV when necessary.
3. Apply orientation correction where appropriate.
4. Improve contrast and readability where necessary.
5. Select a tested recognition-language configuration.
6. Execute OCR.
7. Preserve recognized text.
8. Preserve coordinates/bounding boxes.
9. Preserve confidence.
10. Record engine and model version.

Do not OCR an unlimited number of pages simultaneously.

Use bounded worker concurrency because the development machine has approximately 16 GB RAM.

Do not attempt to load optional large language models alongside OCR by default.

## 11. OCR Evidence and Confidence

For each extracted field, store:

- Field code.
- Human-readable field label.
- Raw extracted value.
- Normalized value.
- Confidence score.
- Page number.
- Bounding box.
- Extraction method.
- OCR/extraction engine.
- Engine version.

A bounding box should use a consistent coordinate convention.

Document whether coordinates are:
- Pixel coordinates.
- Normalized image coordinates.
- Normalized page coordinates.

Convert consistently before highlighting regions in the frontend PDF viewer.

Never confuse OCR confidence with probability that a document is genuine.

Low-confidence extraction should result in review or uncertainty, not an invented value.

## 12. Structured Field Extraction

Extract only the fields required by the selected document type and prototype workflow.

Examples:

Institution:
- Institution name.
- Address.
- Institution identifier.

Certificate:
- Certificate number.
- Issuer.
- Issue date.
- Expiry/validity information.
- Institution/site name.

Building document:
- Building/site identifier.
- Completion date.
- Issuing authority.

Financial document:
- Financial year.
- Organisation/entity name.
- Relevant date and reference.

Always preserve raw and normalized forms separately.

Normalization may include:
- Unicode NFKC normalization.
- Case folding.
- Whitespace normalization.
- Approved punctuation handling.
- Approved aliases.

Do not silently rewrite extracted source values.

Store normalized values as additional representations.

Where a field is uncertain or cannot be parsed, preserve the raw value and flag the uncertainty.

## 13. Date Extraction and Expiry

Extract raw date text first.

Then:
1. Determine the likely date format.
2. Parse it using an explicit, tested parser.
3. Normalize to YYYY-MM-DD where unambiguous.
4. Preserve the original extracted text.
5. Compare against the correct evaluation date.
6. Apply only an identified validity rule.

If parsing is ambiguous, return UNABLE_TO_DETERMINE.

Do not invent expiration dates.

Do not assume a universal Fire Safety Certificate validity period.

Use issuer-specific validity configuration where established.

The five-year structural stability validity specified in the applicable uploaded APH provision must remain distinct from any other certificate's validity rules.

## 14. Document Classification

Classification can use:
- User-selected document type.
- Document text.
- Document keywords.
- Document structure.
- Configured classification rules.

The system may automatically suggest a document category.

The user or authorised reviewer should be able to confirm or correct the classification where required.

Store:
- Predicted category.
- Confidence.
- Classification method/model.
- Model version.
- Human confirmation status.

Do not let a weak classification result silently determine regulatory compliance.

## 15. Source and Application Comparison

Compare document values against:
- Application declarations.
- Synthetic institutional records.
- Synthetic issuer responses.
- Applicable regulatory rules.

Use exact official identifiers when available.

For names and addresses, use appropriate normalization and RapidFuzz candidate similarity as supporting evidence.

Never treat a similarity score as a probability of identity.

Store:
- Application value.
- Extracted document value.
- Source value.
- Normalized comparison values.
- Difference.
- Source reference and version.
- Source timestamp/freshness.
- Relevant rule.

Do not collapse multiple comparison outcomes into a single authenticity score.

## 16. Perceptual Hashing

Use pHash to identify candidate visually similar images.

A basic procedure:

1. Decode image.
2. Normalize orientation and image representation.
3. Calculate perceptual hash.
4. Compare hashes.
5. Calculate Hamming distance.
6. Apply a configurable, tested threshold.
7. Store the result as a candidate duplicate observation.

A pHash match does not prove the documents are identical or fraudulent.

Account for:
- Resizing.
- Compression.
- Brightness differences.
- Cropping.
- Image rotation.

Test using representative synthetic document images.

Do not compare unrelated page images and present the result as a reliable document-duplication verdict.

## 17. Text-Layer versus Visible-Image Comparison

This is an important improvement feature.

Where technically feasible:

1. Extract PDF text-layer content.
2. Render the corresponding page as an image.
3. OCR the rendered image independently.
4. Normalize comparable extracted values.
5. Compare important fields.
6. Record possible disagreements.
7. Preserve the page and image region.
8. Route the observation for human assessment.

Example:

Embedded text layer:
Valid until 31-03-2027.

Visible scanned content:
Valid until 31-03-2026.

Expected behaviour:
- Create a content discrepancy observation.
- Show the two extracted values.
- Show the relevant page.
- Highlight the relevant regions where possible.
- Require reviewer verification.

OCR disagreement is an indicator for review, not proof of intentional alteration.

## 18. Digital Signature Verification

Use PyHanko or a compatible PDF signature-verification implementation.

Keep separate statuses for:

- Signature present.
- Signature structure.
- Byte-range/digest validity.
- Signer certificate.
- Certificate-chain trust.
- Revocation information.
- Signing timestamp.
- Validation availability.

Never treat a mathematically valid signature as automatically trusted without considering the certificate trust policy.

Use clear separate outcomes such as:
- VALID.
- INVALID.
- UNKNOWN.
- UNAVAILABLE.
- NOT_PRESENT.

The initial demonstration may include basic valid/invalid signed-document checks.

Full production-grade certificate trust-chain and long-term validation belong to a later implementation stage unless explicitly required.

Do not generate a fake issuer signature or claim an unsigned PDF is officially certified.

## 19. QR Code and Issuer Verification

Handle QR codes as untrusted input.

Never automatically follow arbitrary URLs embedded in uploaded documents.

If QR resolution is implemented:
- Decode the QR content.
- Inspect the domain.
- Apply an allowlist.
- Use only explicitly authorised endpoints.
- Record the method and source.
- Store the correlation ID and response timestamp.

Use local synthetic issuer fixtures by default.

Support separate verification outcomes:

- VERIFIED.
- MISMATCH.
- EXPIRED.
- PENDING.
- SOURCE_UNAVAILABLE.
- MANUAL_REVIEW_REQUIRED.

Mark all simulated responses clearly.

An unavailable source must never be classified as verified.

## 20. Error Handling

Possible document pipeline failures include:

- Unsupported format.
- Malformed PDF.
- Failed MIME detection.
- Malware detected.
- Scanner unavailable.
- Password-protected document.
- Unreadable scan.
- OCR timeout.
- OCR engine failure.
- Invalid date format.
- Missing extracted fields.
- Storage failure.
- Signature validation failure.

Preserve processing history.

Do not erase original upload records merely because processing failed.

Use the appropriate processing status:

- QUEUED.
- PROCESSING.
- COMPLETED.
- PARTIAL.
- FAILED.
- NEEDS_MANUAL_REVIEW.

Explain failure through appropriate role-specific interfaces.

## 21. Human Review and Evidence Provenance

Every important document-derived discrepancy must be traceable.

Connect:
- Document version.
- PDF page.
- Extracted field.
- OCR bounding box.
- Source record or verification attempt.
- Validation result.
- Applicable rule version.
- Finding.
- Reviewer action.

Persist evidence relationships.

The Evidence Contradiction Explorer must use these stored relationships rather than constructing decorative connections in the frontend.

Preserve previous reviews and document versions.

## 22. Performance and Resource Discipline

The target environment has approximately 16 GB RAM.

Therefore:

- Limit OCR worker concurrency.
- Process PDF pages in bounded batches.
- Avoid unlimited image rendering.
- Avoid keeping unnecessary full-resolution images in memory.
- Store derivatives separately from original files.
- Use asynchronous processing.
- Record per-page OCR timings.
- Benchmark representative sample files.
- Avoid promising fixed OCR execution times without measurement.

Use realistic load tests.

## 23. Testing Requirements

Create tests for:

- Valid PDF.
- Valid JPEG and PNG.
- Unsupported file formats.
- Incorrect MIME/file signature.
- Oversized file.
- Malformed PDF.
- Malware scanner unavailable.
- Duplicate file bytes.
- Resized/compressed image duplicate candidate.
- Searchable PDF.
- Scanned English PDF.
- Scanned Tamil PDF.
- Low-quality scanned PDF.
- Low-confidence extraction.
- Invalid/ambiguous dates.
- Text-layer versus visible-image mismatch.
- Valid signed PDF.
- Invalid signed PDF.
- Unknown certificate trust.
- Missing digital signature.
- Unavailable synthetic issuer.
- Immutable version creation.
- Exact page and field evidence linking.

Test both successful and failure paths.

Keep representative expected outputs in synthetic test fixtures.

## 24. Development Workflow

Before implementing a document feature:

1. Consult the Prototype Specification.
2. Consult the Improvement Report when relevant.
3. Check the corresponding schema v4 entities.
4. Define inputs and outputs.
5. Define processing and failure statuses.
6. Implement the service.
7. Add database persistence.
8. Add tests.
9. Integrate the frontend evidence view.
10. Verify the complete workflow.

Build document functionality incrementally.

Never report an implemented OCR, tamper check, signature check or issuer integration unless it has actually been tested.
