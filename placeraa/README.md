### Placeraa

AI-powered university placement readiness platform

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app placeraa
```

### How it fits together

Placeraa sits on top of Frappe LMS and reuses it: students are Frappe users, courses are `LMS Course`, and assessments are `LMS Quiz` with their `LMS Quiz Submission` results.

```
LMS Quiz Submission --(Quiz Skill)--> Student Skill --> Skill Gap --(Course Skill)--> Recommendation
                                            \--------------> Placement Readiness
```

| DocType | Purpose |
|---|---|
| `Skill` | The skills tracked, grouped in a category that feeds a readiness component |
| `Quiz Skill` | Which skills an LMS quiz measures |
| `Course Skill` | Which skills an LMS course teaches |
| `Student Skill` | A student's current score in a skill |
| `Skill Gap` | Target against current score, with a derived severity |
| `Recommendation` | A course suggested to close a gap |
| `Placement Readiness` | Overall and component readiness for a student |

The rules that turn scores into levels, gaps and readiness are in `placeraa/scoring.py` and `placeraa/services/profile.py`. When a quiz is submitted, `placeraa/services/assessment.py` applies it to the student's profile. MVP simplification: the score in a skill is the percentage of the latest submission of a quiz mapped to it, and a quiz mapped to several skills gives each of them that percentage.

Students read only their own records (`placeraa/permissions.py`).

### Showcase

The student dashboard is at `/placeraa`. A student sees their own, and a System Manager or Moderator can open another student's with `/placeraa?student=<email>`. The data comes from `placeraa.api.dashboard.get_student_dashboard`.

Demo data is created by an idempotent seed that never overwrites existing records:

```bash
bench --site lms.localhost execute placeraa.demo.seed.seed_demo_data
# add --kwargs '{"dry_run": True}' to run it and roll everything back
```

It creates the five skills, five demo courses (tagged `placeraa-demo`) with lessons, an SQL quiz mapped to the SQL skill, and a demo student, `demo.student@placeraa.test`, with their skill profile. The demo password is defined in `placeraa/demo/seed.py` and is only set on a site in developer mode.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/placeraa
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

agpl-3.0
