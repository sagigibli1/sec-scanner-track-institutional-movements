# הגדרת משתני סביבה ו-OAuth / Environment Setup

SEC Scanner משתמש בשני מקורות נתונים שונים. אחד דורש מפתח API חינמי, השני דורש הזדהות בדפדפן פעם אחת. הנה המסלול המלא, שלב אחרי שלב.

SEC Scanner uses two different data sources. One needs a free API key, the other needs a one-time browser sign-in. Here is the full path, step by step.

---

## חלק 1 - מפתח FMP בשביל ה-Skill / FMP API Key for the Skill

ה-Institutional Flow Tracker Skill מושך מידע ממקור שנקרא Financial Modeling Prep (קיצור: FMP). הם נותנים 250 קריאות ביום בחינם, מספיק לעשרות בדיקות ביום.

The Institutional Flow Tracker skill pulls data from a service called Financial Modeling Prep (FMP for short). They give 250 free requests per day, enough for dozens of lookups.

### שלב 1.1 - הרשמה ב-FMP

נכנסים לאתר https://site.financialmodelingprep.com, לוחצים Sign Up, ממלאים אימייל וסיסמה. אין צורך בכרטיס אשראי, אין שום שלב שדורש תשלום. אחרי שמאשרים את האימייל, מגיעים לדאשבורד ובצד ימין למעלה מופיע המפתח (API Key) - מחרוזת של כ-32 תווים. לוחצים על Copy.

Go to https://site.financialmodelingprep.com, click Sign Up, fill in email and password. No credit card needed. After verifying email, you reach the dashboard. The API key (about 32 characters) appears in the top right. Click Copy.

`[SCREENSHOT: FMP signup page]`

`[SCREENSHOT: FMP dashboard with API key visible top-right]`

### שלב 1.2 - להוסיף את המפתח ל-zshrc

המק שלך משתמש ב-zsh. כל פעם שאתה פותח טרמינל חדש הוא קורא קובץ בשם `.zshrc` בתיקיית הבית, ושם נשמרים משתני הסביבה הקבועים. נפתח את הקובץ הזה ונוסיף שורה אחת.

Your Mac uses zsh. Every new terminal reads a file called `.zshrc` in your home folder, and that is where persistent environment variables live. Open that file and add one line.

פותחים את הטרמינל ומריצים:

Open the terminal and run:

```bash
open -e ~/.zshrc
```

אם הקובץ ריק, זה בסדר. מוסיפים בסוף שורה שנראית ככה (להחליף את `YOUR_KEY_HERE` במפתח האמיתי מ-FMP):

If the file is empty, that is fine. Add a line at the bottom that looks like this (replace `YOUR_KEY_HERE` with your real FMP key):

```bash
export FMP_API_KEY="YOUR_KEY_HERE"
```

שומרים את הקובץ, סוגרים את העורך, וחוזרים לטרמינל. כדי שהשורה החדשה תיכנס לתוקף בלי לפתוח טרמינל חדש:

Save the file, close the editor, return to the terminal. To activate the line without opening a new terminal:

```bash
source ~/.zshrc
```

`[SCREENSHOT: .zshrc open in TextEdit with FMP_API_KEY line highlighted]`

### שלב 1.3 - בדיקה שהמפתח עלה

מריצים:

Run:

```bash
echo $FMP_API_KEY
```

צריך להופיע המפתח. אם הפלט ריק, פתחת טרמינל ישן או שכחת לעשות `source`. סגור את הטרמינל ופתח חדש.

The key should print. If the output is empty, you opened an old terminal or forgot to `source`. Close the terminal and open a new one.

---

## חלק 2 - חיבור OAuth ל-EdgarTools / EdgarTools OAuth Flow

ה-EdgarTools MCP לא צריך מפתח API ידני. במקום זה, בפעם הראשונה שקלוד קוד קורא לכלי שלו, נפתח דפדפן עם דף התחברות של גוגל. זה התהליך השלם.

The EdgarTools MCP needs no manual API key. Instead, the first time Claude Code calls one of its tools a browser tab opens with a Google sign-in page. Here is the flow.

### שלב 2.1 - לוודא שה-MCP מותקן

לפני שעושים את ה-OAuth, צריך לוודא שהסקריפט `install/01-edgartools-mcp.sh` רץ בהצלחה. אם לא, חזור לסקריפט הראשי.

Before doing OAuth, make sure `install/01-edgartools-mcp.sh` ran successfully. If not, go back to the main installer.

### שלב 2.2 - לפעיל את ה-OAuth בקלוד קוד

פותחים טרמינל חדש, נכנסים לתיקיית הפרויקט, ומריצים `claude`. בתוך השיחה כותבים שאלה שמפעילה את ה-MCP. למשל:

Open a new terminal, cd into the project folder, and run `claude`. In the conversation, type a question that triggers the MCP. For example:

```
Get me Apple's latest 10-Q filing using the edgar-tools MCP
```

קלוד יזהה שצריך את ה-MCP, יפתח טאב בדפדפן עם דף התחברות. בוחרים את חשבון הגוגל שלך, מאשרים, והטאב יראה הודעה כמו "Authentication complete, you can close this window". סוגרים את הטאב וחוזרים לטרמינל. השאלה תמשיך לרוץ אוטומטית.

Claude will detect it needs the MCP and open a browser tab with a sign-in page. Pick your Google account, approve, and the tab will show something like "Authentication complete, you can close this window". Close the tab and return to the terminal. The query continues automatically.

`[SCREENSHOT: EdgarTools OAuth Google sign-in page]`

`[SCREENSHOT: "Authentication complete" confirmation page]`

### שלב 2.3 - להבין את המגבלה היומית

החשבון החינמי נותן 100 קריאות ליום, מתאפס בחצות לפי שעון UTC (ב-2 בלילה שעון ישראל). שאלה בודדת בקלוד יכולה לצרוך 3-5 קריאות, אז בערך 20-30 שאילתות עמוקות ביום. אם נגמרה המכסה, פשוט מחכים למחר. אין צורך בכרטיס אשראי בשום שלב.

The free tier gives 100 calls per day, resets at midnight UTC (2am Israel time). A single Claude question can burn 3-5 calls, so roughly 20-30 deep queries per day. If the quota runs out, just wait until tomorrow. No credit card needed at any point.

---

## חלק 3 - קובץ .env מקומי לפרויקט / Local Project .env

יש בתיקייה קובץ דוגמה בשם `.env.example`. אם אתה רוצה להחזיק את המפתחות גם ברמת הפרויקט (חוץ מ-zshrc), העתק את הדוגמה לקובץ אמיתי:

There is a template called `.env.example` in this folder. If you want to keep the keys at the project level too (in addition to zshrc), copy the template into a real file:

```bash
cp install/.env.example install/.env
```

ערוך את `install/.env` ומלא את המפתח שלך. הקובץ הזה לא נכנס ל-git, הוא מקומי בלבד. השרת שמריצים בהמשך טוען אותו אוטומטית.

Edit `install/.env` and fill in your key. This file is local-only and ignored by git. The runner loads it automatically.

---

## סיכום בדיקה מהירה / Quick Verify

אחרי שביצעת את שלושת השלבים, הרץ:

After all three steps, run:

```bash
bash scripts/verify.sh
```

אם כל ה-checks ירוקים, אתה מוכן להמשיך למודול. אם משהו אדום, התסריט יגיד לך בדיוק מה חסר.

If all checks are green, you are ready to continue. If anything is red, the script will tell you exactly what is missing.
