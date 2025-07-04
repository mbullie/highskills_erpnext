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
