# UMBRA Artifact Repository

## Source Code and Supplementary Materials

### 1. Ground Truth Dataset/
This directory contains manually annotated labels used to validate and evaluate the accuracy of UMBRA’s detection modules.

The annotations serve as reference ground truth for performance analysis.

---

### 2. Large-Scale-Measurement Dataset/
This directory contains datasets collected from large-scale web crawls.
EU/ → European websites (2000)
USA/ → United States websites(2000)
Tranco-10K/ → Tranco top-ranked websites (10000)

### 3. Lexicons/
This directory provides keyword lists and linguistic indicators used to detect multiple categories of dark patterns, including:

- Cookie information disclosure
- Purpose transparency
- Opt-out pricing
- Legal ambiguity

- These lexicons support the automated text-based detection modules.

- ### 4. Results_Cookies/Cookie_json/ (Limited)
This directory stores collected cookie records in JSON format.

Each file includes information such as:

- Cookie names and domains
- Expiration times
- Security attributes
- Interaction-dependent changes

These records enable security and privacy risk analysis.

### 5. Screenshots (Limited)/
This directory contains a limited subset of banner screenshots.

These images are provided for qualitative validation and illustrative purposes. These final images were used by both researchers to annotate the ground-truth dataset.
