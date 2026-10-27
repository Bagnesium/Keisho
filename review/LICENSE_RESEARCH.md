# Licensing & Redistribution Research

This document provides a source-backed assessment of redistribution constraints for third-party code, datasets, APIs, vocabularies, and trust stores relevant to Keisho.

The root `LICENSE` applies only to Keisho-authored code and documentation.
Third-party and service-derived materials are outside that grant. This review
does not establish redistribution permission for the tracked OpenRouter
catalog snapshots; that status remains unresolved.

---

## 1. Vendored MIT Files (`src/keisho/benchmark/vendor/`)

- **Files Vendored**: `signals.py`, `summary_summarizer.py.txt`, `structured_summarizer.py.txt`, `prompt_parts.py.txt`, `LICENSE` (tracked in `src/keisho/benchmark/vendor/provenance.json`).
- **Upstream Repository**: [`anjilab/agent-handoff-debt`](https://github.com/anjilab/agent-handoff-debt) (commit `5179b1d759be466600c453da8b9078341967ec17`).
- **License**: MIT License (Copyright (c) 2026 Dipesh KC and Anjila Budathoki).
- **Source URL**: [https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/LICENSE](https://github.com/anjilab/agent-handoff-debt/blob/5179b1d759be466600c453da8b9078341967ec17/LICENSE) (local copy at [`src/keisho/benchmark/vendor/LICENSE`](file:///workspace/keisho-wt/license/src/keisho/benchmark/vendor/LICENSE)).
- **Quoted Clause**:
  > "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."
- **Status**: **CONFIRMED**.
- **Redistribution Constraints**:
  - Permissive redistribution in source or binary forms.
  - Mandatory requirement: retain the original copyright notice and permission notice in all copies or substantial portions of the software. The vendored license file is retained at `src/keisho/benchmark/vendor/LICENSE`; no repository-level `NOTICE` file is currently present.

---

## 2. SWE-bench Code & Hugging Face Dataset

### A. SWE-bench Code
- **Repository**: [`SWE-bench/SWE-bench`](https://github.com/SWE-bench/SWE-bench)
- **License URL**: [https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE](https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE)
- **License**: MIT License (Copyright (c) 2023 Carlos E Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, Karthik R Narasimhan).
- **Quoted Clause**:
  > "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."
- **Status**: **CONFIRMED**.
- **Redistribution Constraints**: Permissive; redistribution of SWE-bench harness code or evaluation scripts requires retaining the copyright notice and permission notice.

### B. Hugging Face Dataset: `princeton-nlp/SWE-bench_Verified`
- **Dataset Card URL**: [https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified)
- **Raw README URL**: [https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/raw/main/README.md](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/raw/main/README.md)
- **License Status**: **UNCONFIRMED** on the dataset card.
- **Quoted Clause / Card Finding**:
  - The Hugging Face dataset card metadata explicitly omits a `license:` tag (`cardData.license: None`).
  - The dataset card text ends with:
    > `[More Information needed]`
- **Redistribution Constraints**:
  - While the benchmarking harness on GitHub is MIT-licensed, the dataset consists of 500 validated task instances containing GitHub issues (problem statements, discussions) and pull request patches harvested from 12 open-source Python repositories.
  - The dataset card grants no formal dataset redistribution license (e.g., CC-BY or CDLA).
  - Redistribution of benchmark task instances is governed by the individual upstream repository licenses (e.g. BSD-3, Apache-2.0, MIT) rather than an unconditional blanket MIT license.

---

## 3. OpenRouter Terms of Service regarding `/api/v1/models` Catalog Data

- **Source URL**: [https://openrouter.ai/terms](https://openrouter.ai/terms) (Terms of Service, Last Updated: August 31, 2026).
- **License / Terms Status**: Proprietary service terms; public redistribution of catalog dumps is **RESTRICTED / UNCONFIRMED**.
- **Quoted Clauses**:
  - **Section 12 (Ownership; Proprietary Rights)**:
    > "The visual interfaces, graphics, design, compilation, information, data, computer code (including source code or object code), products, software, services, and all other elements of the Service ('Materials') provided by OpenRouter are protected by intellectual property and other laws. All Materials included in the Service are the property of OpenRouter or our third-party licensors. Except as expressly authorized by OpenRouter, you may not make use of the Materials. OpenRouter reserves all rights to the Materials not granted expressly in these Terms."
  - **Section 7 (Prohibited Conduct)**:
    > "BY USING THE SERVICE, YOU AGREE NOT TO: ...
    > develop, support or use software, devices, scripts, robots or any other means or processes (such as crawlers, browser plugins, add-ons or any other automated technology) to scrape or copy any information on the Site or the Services; ...
    > sell or otherwise transfer the access granted under these Terms or any Materials (as defined in 12) or any right or ability to view, access, or use any Material;"
- **Redistribution Constraints**:
  - OpenRouter explicitly classifies API responses, catalog data, and compilations as proprietary "Materials".
  - The Terms do not contain an open license grant authorizing caching, snapshotting, or public redistribution of `/api/v1/models` endpoint responses (e.g., `analysis/openrouter-catalog-v1.2.0.json`).
  - Distributing static OpenRouter catalog files in a public repository without express authorization is legally unconfirmed and potentially infringes Sections 7 and 12.
  - **Constraint / Recommendation**: Treat catalog data as ephemeral runtime cache obtained directly by end-user client calls, or seek explicit written confirmation from OpenRouter before distributing bundled catalog snapshots.

---

## 4. xarray & sympy Licenses

### A. xarray
- **Repository**: [`pydata/xarray`](https://github.com/pydata/xarray)
- **License URL**: [https://github.com/pydata/xarray/blob/main/LICENSE](https://github.com/pydata/xarray/blob/main/LICENSE)
- **License**: Apache License, Version 2.0 (`Apache-2.0`) — **CONFIRMED**.
- **Quoted Clause (Section 4 - Redistribution)**:
  > "You may reproduce and distribute copies of the Work or Derivative Works thereof in any medium, with or without modifications, and in Source or Object form, provided that You meet the following conditions:
  > (a) You must give any other recipients of the Work or Derivative Works a copy of this License; and
  > (b) You must cause any modified files to carry prominent notices stating that You changed the files; and
  > (c) You must retain, in the Source form of any Derivative Works that You distribute, all copyright, patent, trademark, and attribution notices from the Source form of the Work, excluding those notices that do not pertain to any part of the Derivative Works; and
  > (d) If the Work includes a 'NOTICE' text file as part of its distribution, then any Derivative Works that You distribute must include a readable copy of the attribution notices contained within such NOTICE file..."
- **Redistribution Constraints**:
  - Provide a copy of the Apache-2.0 license.
  - Provide prominent notices on any modified files.
  - Retain all copyright, patent, trademark, and attribution notices.
  - Retain NOTICE file attributions if applicable (pydata/xarray has no separate NOTICE file upstream).

### B. sympy
- **Repository**: [`sympy/sympy`](https://github.com/sympy/sympy)
- **License URL**: [https://github.com/sympy/sympy/blob/master/LICENSE](https://github.com/sympy/sympy/blob/master/LICENSE)
- **License**: BSD 3-Clause License (`BSD-3-Clause`) — **CONFIRMED** (Copyright (c) 2006-2023 SymPy Development Team).
- **Quoted Clause**:
  > "Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
  >   a. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
  >   b. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
  >   c. Neither the name of SymPy nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission."
- **Redistribution Constraints**:
  - Retain copyright notice, 3-clause conditions, and disclaimer in all source redistributions.
  - Reproduce copyright notice, conditions, and disclaimer in documentation/materials for binary distributions.
  - No endorsement/promotion using "SymPy" or contributor names without prior written permission.
  - Note: Upstream SymPy `LICENSE` also embeds notices for bundled components: Diofant (BSD-3), multipledispatch (BSD-3), PyDy (BSD-3), and latex2sympy (MIT).

---

## 5. tiktoken `o200k_base` Vocab File & Mozilla / certifi CA Bundle

### A. tiktoken Code vs. `o200k_base` Vocab File
- **tiktoken Code**:
  - **License URL**: [https://github.com/openai/tiktoken/blob/main/LICENSE](https://github.com/openai/tiktoken/blob/main/LICENSE)
  - **License**: MIT License (Copyright (c) 2022 OpenAI, Shantanu Jain) — **CONFIRMED**.
  - **Quoted Clause**:
    > "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."
- **`o200k_base.tiktoken` Vocabulary File**:
  - **Asset URL**: [https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken](https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken)
  - **License Status**: **UNCONFIRMED**.
  - **Quoted / Structural Finding**:
    The downloaded file `o200k_base.tiktoken` consists strictly of raw base64 BPE tokens and rank indices (beginning `IQ== 0\nIg== 1...`) with no embedded license header or copyright declaration. The `openai/tiktoken` repository downloads this asset dynamically at runtime from Azure Blob Storage rather than distributing it within the Git tree. OpenAI has issued no explicit license grant extending the repository's MIT terms to external model vocabulary binaries.
  - **Redistribution Constraints**: Direct redistribution of the raw `.tiktoken` file is legally unconfirmed; projects should rely on `tiktoken`'s runtime download and user-side caching mechanism (`TIKTOKEN_CACHE_DIR`) rather than committing and redistributing the vocabulary asset directly.

### B. Mozilla / certifi CA Bundle (MPL-2.0)
- **Source URLs**:
  - Certifi License: [https://github.com/certifi/python-certifi/blob/master/LICENSE](https://github.com/certifi/python-certifi/blob/master/LICENSE)
  - Mozilla NSS root certificates: [https://hg.mozilla.org/mozilla-central/file/tip/security/nss/lib/ckfw/builtins/certdata.txt](https://hg.mozilla.org/mozilla-central/file/tip/security/nss/lib/ckfw/builtins/certdata.txt)
  - Mozilla Public License 2.0: [https://www.mozilla.org/MPL/2.0/](https://www.mozilla.org/MPL/2.0/)
- **License**: Mozilla Public License Version 2.0 (`MPL-2.0`) — **CONFIRMED**.
- **Quoted Clauses**:
  - **Certifi LICENSE header**:
    > "This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/."
  - **MPL-2.0 Section 3.1 (Distribution of Source Form)**:
    > "All distribution of Covered Software in Source Code Form, including any Modifications that You create or to which You contribute, must be under the terms of this License. You must inform recipients that the Source Code Form of the Covered Software is governed by the terms of this License, and how they can obtain a copy of this License."
  - **MPL-2.0 Section 3.3 (Distribution of a Larger Work)**:
    > "You may create and distribute a Larger Work under terms of Your choice, provided that You also comply with the requirements of this License for the Covered Software."
  - **MPL-2.0 Section 3.4 (Notices)**:
    > "You may not remove or alter the substance of any license notices (including copyright notices, patent notices, disclaimers of warranty, or limitations of liability) contained within the Source Code Form of the Covered Software..."
- **Redistribution Constraints**:
  - Weak, file-level copyleft: any redistribution of the CA bundle file itself (e.g., `openrouter-ca-v1.2.0.pem`) must remain subject to MPL-2.0.
  - When distributed as part of a "Larger Work" (Keisho), the rest of the project can be licensed under Apache-2.0 or MIT, provided:
    1. The CA bundle retains its MPL-2.0 notice.
    2. Downstream recipients are informed that the CA bundle is governed by MPL-2.0 and told how to obtain the source.

---

## 6. Recommended Project License & NOTICE Contents

### Recommended License: Apache License, Version 2.0 (`Apache-2.0`)
- **Compatibility**: Apache-2.0 seamlessly incorporates permissive inbound code: MIT (`agent-handoff-debt`, `SWE-bench`, `tiktoken`), BSD-3-Clause (`sympy`), and Apache-2.0 (`xarray`).
- **Larger Work Integration**: Under MPL-2.0 Section 3.3, an Apache-2.0 codebase can distribute the Mozilla/certifi CA bundle as a "Larger Work" without license conflict, as long as the CA bundle file itself remains under MPL-2.0.
- **Patent & Contribution Protection**: Unlike MIT, Apache-2.0 provides an explicit patent grant and patent defense clause (Section 3), offering legal protection for reproducibility scaffolds, agent communication protocols, and evaluation tooling.
- **Attribution Convention**: Apache-2.0 formalizes third-party notices via Section 4(d) through a standardized `NOTICE` file.

*(Alternative: An MIT license for Keisho is also viable if all dependencies, trust roots, and vocabularies are completely decoupled and fetched dynamically at installation rather than bundled into repository source trees).*

---

### Proposed `NOTICE` Contents

```text
Keisho
Copyright 2026 The Keisho Authors

This product includes software developed as part of the Keisho research project.

===============================================================================
Third-Party Attributions and Acknowledgments
===============================================================================

1. Vendored Agent Handoff Debt Code (src/keisho/benchmark/vendor/):
   Copyright (c) 2026 Dipesh KC and Anjila Budathoki
   Licensed under the MIT License.
   Source: https://github.com/anjilab/agent-handoff-debt

2. SWE-bench:
   Copyright (c) 2023 Carlos E Jimenez, John Yang, Alexander Wettig,
   Shunyu Yao, Kexin Pei, Ofir Press, Karthik R Narasimhan
   Licensed under the MIT License.
   Source: https://github.com/SWE-bench/SWE-bench

3. SymPy:
   Copyright (c) 2006-2023 SymPy Development Team
   Licensed under the BSD 3-Clause License.
   Source: https://github.com/sympy/sympy

4. Xarray:
   Copyright 2014-2023 xarray Developers
   Licensed under the Apache License, Version 2.0.
   Source: https://github.com/pydata/xarray

5. Tiktoken:
   Copyright (c) 2022 OpenAI, Shantanu Jain
   Licensed under the MIT License.
   Source: https://github.com/openai/tiktoken

6. Mozilla CA Certificate Bundle (Certifi):
   This product includes CA certificates extracted from Mozilla NSS roots.
   Licensed under the Mozilla Public License, Version 2.0 (MPL-2.0).
   Source: https://github.com/certifi/python-certifi
   You may obtain a copy of the MPL 2.0 at http://mozilla.org/MPL/2.0/.

===============================================================================
Data and API Disclaimers
===============================================================================

- SWE-bench Verified Dataset (princeton-nlp/SWE-bench_Verified):
  Benchmark task instances, issue statements, and patch excerpts originate
  from individual upstream open-source repositories and are subject to their
  respective original repository licenses.

- OpenRouter API Catalog Data:
  OpenRouter service information and catalog data are proprietary materials of
  OpenRouter, Inc. (https://openrouter.ai/terms). Catalog files are unauthenticated
  snapshots for experimental reproducibility and are not licensed for independent
  commercial redistribution.

- OpenAI Tokenizer Vocabularies:
  BPE vocabulary data files (e.g. o200k_base.tiktoken) are distributed by OpenAI
  via Azure storage endpoints. Redistribution licensing remains unconfirmed;
  runtime fetching via the official tiktoken package is recommended.
```

## Sources (re-checked by the reviewer via GitHub API `license.spdx_id`, 2026-10-23)
- SWE-bench harness: https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE (MIT)
- SWE-bench Verified dataset card: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified
- tiktoken: https://github.com/openai/tiktoken/blob/main/LICENSE (MIT); o200k_base vocab has no separate stated license — do not vendor, keep download-by-hash.
- certifi CA bundle: https://github.com/certifi/python-certifi/blob/master/LICENSE (MPL-2.0; GitHub reports NOASSERTION); MPL FAQ: https://www.mozilla.org/en-US/MPL/2.0/FAQ/
- sympy: https://github.com/sympy/sympy/blob/master/LICENSE (BSD-3-Clause; GitHub API returned no SPDX)
- xarray: https://github.com/pydata/xarray/blob/main/LICENSE (Apache-2.0)
- Vendored anjilab/agent-handoff-debt: https://github.com/anjilab/agent-handoff-debt (MIT)
- Apache-2.0 text: https://www.apache.org/licenses/LICENSE-2.0 ; MIT text: https://opensource.org/license/mit
- OpenRouter terms: https://openrouter.ai/terms

Reviewer recommendation: Apache-2.0 (or MIT) for Keisho's own code + NOTICE crediting the vendored MIT code. No LICENSE file added (owner decision).
