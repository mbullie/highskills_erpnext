### Highskills Erpnext

Highskills Erpnext custom app

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/mbullie/highskills_erpnext.git --branch master
bench install-app highskills_erpnext
```

### Upgrade

```bash
cd $PATH_TO_YOUR_BENCH/apps/highskills_erpnext
git pull
bench --site your-site-name migrate
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/highskills_erpnext
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit

## PDF Digital Signing (PyHanko)

This app can optionally sign generated PDFs using PyHanko and a PKCS#12 (PFX) key.
Configuration is read exclusively from your site's `site_config.json` under the `pdf_sign` key.

Example `site_config.json` snippet:

```json
"pdf_sign": {
	"enabled": true,
	"pfx_path": "C:\\\\secrets\\\\cert.p12",
	"pfx_password": "your-pfx-password",
	"visible": true,
	"page_number": 0,
	"box": [50, 50, 250, 120],
	"stamp_image_path": "C:\\\\secrets\\\\stamp.png",
	"stamp_text": "Signed by Highskills"
}
```

Notes:
- `enabled` (bool): when true, the app will attempt to sign PDFs produced by Frappe's `get_pdf`.
- `pfx_path` (string): path to the PKCS#12 (.p12/.pfx) file. Required when `enabled` is true.
- `pfx_password` (string): password for the PFX file.
- `visible` (bool): whether to create a visible signature appearance. If true, `stamp_image_path` is required.
- `page_number` (int): 0-based page index for the visible signature.
- `box` (list): coordinates [x1, y1, x2, y2] in PDF points (1 pt = 1/72 in).
- `stamp_image_path` (string): path to the PNG/JPEG image used as the visible stamp. Required when `visible` is true.

Startup validation:
When `pdf_sign.enabled` is true, the app validates required configuration at startup and will fail fast with a clear error if required keys are missing or files are not found. This helps prevent silent misconfiguration in production.

Testing quick steps (bench console):

1. Ensure dependencies are installed (in your site environment):

```powershell
pip install -e .
pip install pyhanko
```

2. From bench console (adjust site name):

```python
from frappe.utils.pdf import get_pdf
html = "<html><body><h1>Hello</h1></body></html>"
pdf = get_pdf(html)  # Will be signed if site_config.json has pdf_sign.enabled = true
open('/tmp/test_signed.pdf','wb').write(pdf)
```

If signing is enabled but misconfigured (missing pfx or stamp image when visible), bench will raise a clear error on startup.
