# MigraDiff

<div align="center">

**בחרו שפה:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — כלי להשוואת סכמות PostgreSQL

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**פורק זה הוא הפורק המתוחזק באופן פעיל של [djrobstep/migra](https://github.com/djrobstep/migra).**

migra משווה בין שתי סכמות מסדי נתונים של PostgreSQL ומייצר את סקריפט ההגירה (migration) SQL הדרוש כדי להפוך אחת לשנייה. שלבו אותו בצנרת ה-CI שלכם ותפסיקו לכתוב `ALTER TABLE` ידנית.

---

## למה הפורק הזה

הגרסה המקורית של `migra` הוכרזה כמופקדת (deprecated) רשמית ב-2024. הפורק הזה ממשיך מאותה נקודה — מתקן בעיות ידועות, מוסיף תמיכה ב-Python 3.12+, ומרחיב כיסוי לתכונות PostgreSQL מתקדמות.

אם השתמשתם ב-`djrobstep/migra`, זהו ההמשך הישיר שלכם. שום דבר לא השתנה בדרך שבה הכלי עובד. אנחנו רק שומרים עליו פעילים ומשפרים אותו.

**הערה לגבי השמות:** זהו פורק קהילתי עצמאי. פקודת ה-CLI נשארת `migra` לתאימות לאחור עם סקריפטים וצנרת קיימים. שם החבילה הוא `migradiff` כדי להבדיל אותו מהגרסה המופקדת המקורית. אם אתם מחפשים את djrobstep/migra המקורי, הוא בארכיון בכתובת https://github.com/djrobstep/migra.

---

## התחלה מהירה

### התקנה

```bash
pip install migradiff
```

דרוש Python 3.10+ ומופע PostgreSQL רץ (12+).

להתקנה מקוד המקור:

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### שימוש בסיסי

כוונו את migra לשני חיבורי מסדי נתונים והוא יפיק את ה-DDL הדרוש להגירה מאחד לשני:

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

הפלט הוא SQL פשוט — בצנרת, סקירה, יישום:

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### דמפים של סכמה (ללא צורך בחיבור חי)

אם אינכם יכולים או רוצים לכוון את migra למסד נתונים חי, השתמשו ב-`pg_dump -s` כדי לייצר דמפ סכמה ולהשוות אותו במקום:

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

זו הגישה המומלצת עבור צנרת CI וסביבות רגישות לאבטחה — אין צורך בפרטי התחברות לסביבת הייצור.

### תיקיית הגירות (ללא צורך במסד נתונים חי של הסעיף)

אם מצב היעד שלכם מוגדר על ידי תיקייה של קבצי הגירה:

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff מחיל את ההגירות על מסד נתונים זמני ומשווה את התוצאה. תומך ב-Supabase, Flyway ובמוסכמות שמות מספריות סטנדרטיות.

### מוגבל לסכמה מסוימת

```bash
# סכמה בודדת
migra --schema myschema postgres://db_a postgres://db_b

# סכמות מרובות (מופרדות בפסיקים)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### פלט JSON

לצריכה פרוגרמטית או צנרת CI:

```bash
migra --output json postgres://db_a postgres://db_b
```

הפלט כולל סיווג סיכונים לכל הצהרה (`safe`, `warning`, `destructive`) וסיכום עם רמת סיכון כוללת.

---

## הסבר מבוסס AI (אופציונלי)

MigraDiff יכול להסביר כל הגירה בשפה פשוטה — מה כל שינוי עושה, אילו סיכונים הוא נושא, וחלופות בטוחות יותר לפעולות הרסניות.

    migra --explain postgres://db_a postgres://db_b

פלט:

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

מופעל על ידי Claude (Anthropic). הביאו מפתח API משלכם — שום נתונים לא נשלחים לשרתי MigraDiff.

### הגדרה

התקינו את תוספות ה-AI:

    pip install migradiff[ai]

הגדירו את מפתח ה-API שלכם פעם אחת:

    migra --setup-ai

או הגדירו משתנה סביבה:

    export ANTHROPIC_API_KEY=sk-ant-...

קבלו מפתח API בכתובת https://console.anthropic.com

### יצירת רולבק מבוססת AI (--rollback)

צרו את הגירת ההחזרה המדויקת — ה-SQL הדרוש לביטול כל הגירה:

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff משתמש בהקשר סכמת המקור שלכם כדי לשחזר במדויק ביטולים של DROP TABLE ו-DROP COLUMN. פעולות בלתי הפיכות (TRUNCATE, DELETE המוני) מסומנות באופן מפורש.

שלבו עם --explain לקבלת תמונה מלאה:

    migra --explain --rollback postgres://db_a postgres://db_b

דורש `pip install migradiff[ai]` ומפתח API של Anthropic.

### יועץ ביצועים מבוסס AI (--advise)

לפני יישום כל הגירה, קבלו הערכת סיכוני ביצועים — התנהגות נעילה, סיכון לשכתוב טבלה, וחלופות ללא השבתה:

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff מנתח כל הצהרה עבור סיכונים ספציפיים ל-PostgreSQL: נעילות טבלה, שכתובים מלאים, אובדן נתונים בלתי הפיך. כאשר מסופק חיבור חי, מספרי השורות בטבלאות משמשים להערכת משך הנעילה בקנה המידה האמיתי של הנתונים שלכם.

שלבו את כל שלוש תכונות ה-AI לקבלת תמונה מלאה:

    migra --explain --advise --rollback postgres://db_a postgres://db_b

דורש pip install migradiff[ai] ומפתח API של Anthropic.

### מחולל הגירות מבוסס AI (--generate)

תארו מה אתם רוצים בשפה פשוטה — MigraDiff מייצר את SQL ההגירה המבוסס על הסכמה האמיתית שלכם:

    migra --generate "add email verification to users table" \
      postgres://db_production

בניגוד לכלי AI גנריים, MigraDiff מכיר את שמות הטבלאות האמיתיים, סוגי העמודות והאילוצים שלכם — ללא שמות עמודות או סוגים שגויים.

צרו וסקרו מיד את הסיכון:

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

דורש pip install migradiff[ai] ומפתח API של Anthropic.

---

## הגדרת סביבת פיתוח

חבילת הבדיקות דורשת מופע PostgreSQL רץ. הדרך הקלה ביותר להשיג אחד היא דרך Docker Compose:

```bash
docker compose up -d
```

פעולה זו מתחילה קונטיינר Postgres 16 ב-localhost:5432 עם אימות trust. אין צורך בסיסמה.

לעצירה:

```bash
docker compose down
```

הנתונים נשמרים בין הפעלות מחדש דרך הווליום `migradiff-pgdata`. לאיפוס מלא:

```bash
docker compose down -v
```

---

## Docker

אין סביבת Python? השתמשו בתמונה הרשמית:

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

הוסיפו השוואת סכמות לוורק פלו של בקשת המשיכה (pull request) שלכם:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

גרמו לבנייה להיכשל באופן אוטומטי אם מתגלות פעולות הרסניות:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

השתמשו בקבצי דמפ סכמה במקום חיבורים חיים:

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

ראו [docs/action-usage.md](docs/action-usage.md) לאפשרויות תצורה מלאות.

---

## הוק Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

ראו `pre-commit-config.example.yaml` בשורש המאגר לאפשרויות תצורה מלאות.

---

## מה migra מבין

- טבלאות, עמודות, אילוצים, אינדקסים
- תצוגות (Views) ותצוגות מהוות (Materialized Views)
- פונקציות ופרוצדורות שמורות
- רצפים (Sequences)
- טיפוסי enum, טיפוסים מורכבים, דומיינים
- מדיניות אבטחת רמת שורה (Row-Level Security, RLS)
- עוטפי נתונים חיצוניים (Foreign Data Wrappers)
- הרשאות ברמת עמודה
- טבלאות מחולקות (Partitioned Tables)
- הערות אובייקט (`COMMENT ON`)

---

## שיפורים לעומת הגרסה המקורית

| תחום | גרסה מקורית (מופקדת) | הפורק הזה |
|---|---|---|
| Python 3.12+ | אזהרות הפקדה | נקי — ללא אזהרות |
| מדיניות RLS | חלקית, באג שוויון | CREATE/DROP מלא, תמיכה בחלוקה |
| הודעות שגיאה | לא ברורות בסוגים לא נתמכים | ברות פעולה עם שם אובייקט וקישור לבעיה |
| דגל --schema | מקרי קצה במסדי נתונים מרובי סכמות | מופרד בפסיקים, תלויות חוצות סכמה נפתרו |
| קלט pg_dump | לא נתמך | מצב `--from-file` מדרגה ראשונה |
| פלט JSON | לא נתמך | `--output json` עם סיווג סיכונים |
| תמונת Docker | אין | `ghcr.io/migradiff/migra` |
| GitHub Action | אין | `migradiff/migra-action` |
| הוק Pre-commit | אין | `.pre-commit-hooks.yaml` |
| סביבת פיתוח | פקודות Docker ידניות | `docker compose up -d` |
| הסבר AI | אין | דגל `--explain` עם Claude — הסבר הבדלים בשפה פשוטה, ניתוח סיכונים, חלופות בטוחות יותר |
| השוואת COMMENT ON | לא נתמך | השוואה מלאה — הוספה/שינוי/הסרה על כל סוגי האובייקטים |

ראו [CHANGELOG.md](CHANGELOG.md) להיסטוריית התיקונים המלאה.

---

## מגבלות ידועות

migra מייצר את ה-SQL להשוואה — הוא לא מחיל אותו. סקרו כל סקריפט שנוצר לפני הרצה מול סביבת הייצור. פעולות הרסניות (`DROP TABLE`, `DROP COLUMN`) מסומנות במצב פלט JSON אך אינן נחסמות במצב SQL פשוט.

migra דורש חיבור PostgreSQL חי כדי לבחון סכמות, או קבצי דמפ סכמה דרך `--from-file`. הוא לא מנתח טקסט DDL גולמי.

---

## תרומה

דיווחי באגים ו-PRs מתקבלים בברכה. אם אתם מתקנים משהו שדווח ב-`djrobstep/migra`, ציינו את מספר הבעיה ב-PR שלכם — זה עוזר לנו לעקוב אחר מה שהקהילה הכי זקוקה לתיקונו.

```bash
git clone https://github.com/migradiff/migra
cd migra
docker compose up -d
pip install -e ".[dev]"
pytest
```

---

## רישיון

MigraDiff הוא **חינמי וקוד פתוח** תחת רישיון MIT.

**כל התכונות עובדות עבור כולם.** אין חומות תשלום, אין הגבלות קוד, אין חסימות.

### סיפור קצר

ביליתי יותר מ-8 שנים כמהנדס בפיליפס, תומך במערכות IT של בתי חולים ששומרות על בטיחות המטופלים. כאשר הקרן שרכשה את החטיבה שלנו פיטרה אותי, הייתי בן 50+ בשוק שבו גיל משנה. למצוא עבודה אחרת הפך כמעט בלתי אפשרי. אני עדיין צריך לפרנס את משפחתי ולהניח אוכל על השולחן.

זו הסיבה ש-MigraDiff קיים. אני בונה כלים שעוזרים לכם, כי ככה אני נשאר מועסק.

### הבקשה

**אם אתם סטודנטים, חובבים, או פרויקט קוד פתוח:** רישיון MIT, חינם לנצח. אין צורך בהסכם.

**אם אתם חברה למטרות רווח המשתמשת ב-MigraDiff:** אנא חתמו על הסכם רישיון עסקי. זה לא על חסימת קוד—כל תכונה נשארת בחינם, אתם מריצים אותה מקומית, שום דבר לא משתנה עבורכם טכנית. זה על הגינות: אם הכלי שלי עוזר לכם להרוויח כסף, עזרו לי להאכיל את משפחתי.

אתם עדיין הבעלים של הכל. אתם שולטים בנתונים שלכם. אתם ניגשים לכל התכונות. אנחנו רק שקופים לגבי איך אנחנו מקיימים את הפיתוח.

אני לא מבקש צדקה. אני מבקש הגינות.

[קבלו רישיון עסקי](https://lateos.ai/license) | [צפו ברישיון MIT](LICENSE)

---

## תודות

פרויקט זה הוא פורק של [djrobstep/migra](https://github.com/djrobstep/migra), שנוצר ותוחזק במקור על ידי Robert Lechte. מנוע ההשוואה הליבה הוא עבודתו. אנו אסירי תודה על כך.
