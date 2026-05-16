# Workflows

ה-slash commands של הקורס. כל command הוא prompt template שקלוד מריץ. כל אחד כותב JSON ל-`data/snapshots/` לפי החוזה ב-`SCHEMAS.md`.

## Daily flow

1. בוקר: `/insider-watch` -> מרענן Form 4 לטיקרים החמים.
2. אחרי זה: `/morning-brief` -> מצליב הכל ומחזיר טופ 5.
3. אחרי דוחות 13F (כל 45 יום): `/flow-track {guru_id}` לכל גורו ברשימה.
4. כשמתחשק להשוות רבעונים: `/portfolio-diff {guru_id} {from_q} {to_q}`.
5. סוף שבוע: `/weekly-newsletter` -> כותב ניוזלטר בעברית.

## Commands

### `/insider-watch`

- מה: מושך Form 4 (טריידים של בכירים) ל-90 ימים אחרונים, לכל הטיקרים ברשימה `insider_watch` מתוך `data/watchlist.json`.
- מתי: כל בוקר, או לפני `/morning-brief`.
- מה כותב: `data/snapshots/insider-{TICKER}.json` (אחד לכל טיקר).
- חוסך מכסה: לא רץ פעמיים באותו יום על אותו טיקר. אם כבר יש סנאפ עם `as_of` היום, מדלג.
- מסמן בצ'אט: קניות מעל מיליון דולר ומכירות מעל 5 מיליון.

### `/flow-track {guru_id}`

- מה: מושך את ה-13F האחרון של גורו ספציפי (`berkshire_hathaway`, `michael_burry`, `bill_ackman`, וכו'). אם הזמין, מפעיל גם את ה-skill `institutional-flow-tracker` בשביל tier-weighting.
- מתי: פעם ברבעון אחרי שדוחות 13F מתפרסמים (45 יום אחרי סוף הרבעון).
- מה כותב: `data/snapshots/holdings-{guru}-{quarter}.json`.
- חוסך מכסה: אם הקובץ של הרבעון הזה כבר קיים עם אותו `filing_date`, מדלג.
- מסמן בצ'אט: top 5 פוזיציות, ואם ה-`lag_days` מעל 50 - אזהרה שהדאטה ישן.

### `/portfolio-diff {guru_id} {from_q} {to_q}`

- מה: משווה שני קבצי holdings קיימים של אותו גורו ומחזיר diff עם new / exited / increased / decreased.
- מתי: כשרוצים לראות מה השתנה אצל באפט מהרבעון שעבר.
- מה כותב: `data/snapshots/diff-{guru}-{from_q}-{to_q}.json`.
- חוסך מכסה: command offline לחלוטין. שום קריאת API. רק קבצים קיימים.
- דרישה מוקדמת: שני קבצי `holdings-*.json` חייבים להיות קיימים. אם חסר אחד, ה-command אומר לרוץ `/flow-track` קודם.

### `/thirteen-d {ticker}`

- מה: מושך 13D ו-13G של מי שמחזיק יותר מ-5% במניה. מסמן אם יש פאלר 13D פעיל (אקטיביסט) על המניה.
- מתי: כשרוצים לראות מי בעלי המניות הגדולים של חברה, או לחפש אקטיביסטים שנכנסו לפוזיציה.
- מה כותב: `data/snapshots/thirteen-d-{TICKER}.json`.
- חוסך מכסה: אם יש סנאפ מהיום, מדלג. עד 5 קריאות EdgarTools לריצה.
- מסמן בצ'אט: top 3 בעלי מניות, ודגל אדום אם יש 13D פעיל.

### `/exec-comp {ticker}`

- מה: שולף DEF 14A (proxy statement) ומחזיר את השכר של המנכ"ל ו-5 הבכירים הכי משולמים. כולל salary, bonus, stock awards, options, total.
- מתי: פעם בשנה אחרי שמתפרסם ה-proxy (בדרך כלל מרץ-מאי לחברות עם שנה קלנדרית).
- מה כותב: `data/snapshots/exec-comp-{TICKER}.json`.
- חוסך מכסה: אם הסנאפ הקיים תואם ל-`filing_date` של ה-DEF 14A האחרון, מדלג. עד 4 קריאות EdgarTools לריצה.
- מסמן בצ'אט: שכר מנכ"ל כולל + יחס שכר מנכ"ל לעובד חציוני אם נחשף.

### `/morning-brief`

- מה: האורקסטרטור היומי. מצליב Form 4 + 13F + signals מ-Institutional Flow Tracker על הווצ'-ליסט. נותן ציון 0-10 לכל טיקר.
- מתי: כל בוקר מסחר.
- מה כותב: `data/snapshots/screener-{YYYY-MM-DD}.json`.
- מה מציג: טופ 5 טיקרים מדורגים בעברית. כולל אזהרת stale-data אם מקור 13F ישן מ-50 יום.
- חוסך מכסה: מרענן רק ~10 טיקרים חמים, השאר נשארים cached. מפעיל את skill ה-Flow Tracker פעם אחת בלבד לכל ריצה.

### `/weekly-newsletter`

- מה: סורק את כל הסנאפים מ-7 הימים האחרונים ובוחר 5-10 כותרות עיקריות.
- מתי: סוף שבוע (שישי או שבת).
- מה כותב: `data/snapshots/newsletter-{week_start}.json`. שדות `headline_he` ו-`context_he` בעברית מדוברת.
- חוסך מכסה: לא נוגע ב-API חיצוני. רק קורא מהדיסק.

## Files produced (cheat sheet)

| Command                            | Output file                                     | Schema in SCHEMAS.md |
| ---------------------------------- | ----------------------------------------------- | -------------------- |
| `/insider-watch`                   | `data/snapshots/insider-{TICKER}.json`          | #2                   |
| `/flow-track {guru}`               | `data/snapshots/holdings-{guru}-{quarter}.json` | #1                   |
| `/portfolio-diff {guru} {q1} {q2}` | `data/snapshots/diff-{guru}-{q1}-{q2}.json`     | #3                   |
| `/thirteen-d {ticker}`             | `data/snapshots/thirteen-d-{TICKER}.json`       | #6                   |
| `/exec-comp {ticker}`              | `data/snapshots/exec-comp-{TICKER}.json`        | #7                   |
| `/morning-brief`                   | `data/snapshots/screener-{YYYY-MM-DD}.json`     | #4                   |
| `/weekly-newsletter`               | `data/snapshots/newsletter-{week_start}.json`   | #5                   |

## Rules every command follows

- Atomic writes: write to `*.tmp` then rename.
- Validate JSON against the schema before writing. No `null` in required fields.
- Quotas: EdgarTools hosted free tier = 100 calls/day. FMP free tier = 250 calls/day. Commands batch, cache, and skip if a snapshot from today already exists.
- 45-day 13F lag is real. Every command that touches 13F adds `filing_date` + `lag_days` and warns in chat if `lag_days > 50`.
- כל הצ'אט בעברית. שמות מותגים בעברית בתוך משפט עברי (קלוד קוד, באפט). ISO dates only.
- אסור em dash. רק `-` רגיל.

## Where to add a new command

`.claude/commands/{name}.md` עם YAML frontmatter (`name`, `description`) ו-prompt body שמסביר לקלוד בדיוק איזה tools לקרוא, איזה JSON לפלוט, ולאן לכתוב. עד 200 שורות.
