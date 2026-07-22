// utils/extractClaimFields.js
//
// Rule-based extraction of claim fields from a single freeform speech
// transcript (Kannada and/or English, mixed). This is intentionally
// heuristic: it looks for anchor words/phrases and grabs nearby tokens.
// It will not be perfect for every way a farmer might phrase things -
// that's exactly why every extracted field still lands in an editable
// form field for the farmer to review and correct.
//
// Groq Whisper transcripts of Kannada speech frequently misspell common
// words (vowel-sign swaps, dropped/added consonants, suffix attachment
// like ಜಿಲ್ಲೆ -> ಜಿಲ್ಲೆಯ). To handle this without any LLM involved, all
// keyword/anchor matching below is done token-by-token using a small
// Levenshtein-distance fuzzy comparison, with a strict distance cap so a
// field is only ever filled on a high-confidence match. No network calls,
// no dependencies.
//
// Returns an object containing ONLY the keys it managed to detect, e.g.
// { farmer_name: "...", crop_type: "..." }. Fields it couldn't find are
// omitted, so merging this into existing formData never blanks out
// something the farmer already filled in. This function never throws -
// any unexpected input just results in fewer (or zero) fields detected.

const DAMAGE_TYPE_KEYWORDS = [
    { value: "flood", keywords: ["flood", "ಪ್ರವಾಹ", "ನೆರೆ"] },
    { value: "drought", keywords: ["drought", "ಬರ"] },
    { value: "hailstorm", keywords: ["hailstorm", "hail", "ಆಲಿಕಲ್ಲು"] },
    { value: "pest_attack", keywords: ["pest", "ಕೀಟ", "ಹುಳು"] },
  ];
  
  const CROP_KEYWORDS = [
    { value: "Ragi", keywords: ["ragi", "ರಾಗಿ"] },
    { value: "Paddy", keywords: ["paddy", "rice", "ಭತ್ತ", "ಅಕ್ಕಿ"] },
    { value: "Cotton", keywords: ["cotton", "ಹತ್ತಿ"] },
    { value: "Maize", keywords: ["maize", "corn", "ಮೆಕ್ಕೆಜೋಳ", "ಜೋಳ"] },
    { value: "Sugarcane", keywords: ["sugarcane", "ಕಬ್ಬು"] },
    { value: "Groundnut", keywords: ["groundnut", "peanut", "ಶೇಂಗಾ", "ಕಡಲೆಕಾಯಿ"] },
    { value: "Tur", keywords: ["tur", "pigeon pea", "ತೊಗರಿ"] },
  ];
  
  // Each anchor is a phrase, expressed as its individual words, so it can be
  // located as a run of adjacent (fuzzily-matched) tokens regardless of
  // language. Tried in order - more specific/reliable phrases first, so
  // e.g. "ನನ್ನ ಹೆಸರು" (a strong, unambiguous "my name is") is preferred
  // over the much more ambiguous standalone "ನಾನು" ("I ...").
  const NAME_ANCHORS = [
    ["farmer", "name", "is"],
    ["my", "name", "is"],
    ["name", "is"],
    ["ನನ್ನ", "ಹೆಸರು"],
    ["ಹೆಸರು"],
    ["ನಾನು"],
  ];
  
  const DISTRICT_ANCHORS = [["district"], ["ಜಿಲ್ಲೆ"]];
  const VILLAGE_ANCHORS = [["village"], ["ಗ್ರಾಮ"], ["ಹಳ್ಳಿ"]];
  
  const MONTHS_EN = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
  ];
  
  const MONTHS_KN = {
    "ಜನವರಿ": 0, "ಫೆಬ್ರವರಿ": 1, "ಮಾರ್ಚ್": 2, "ಏಪ್ರಿಲ್": 3, "ಮೇ": 4, "ಜೂನ್": 5,
    "ಜುಲೈ": 6, "ಆಗಸ್ಟ್": 7, "ಸೆಪ್ಟೆಂಬರ್": 8, "ಅಕ್ಟೋಬರ್": 9, "ನವೆಂಬರ್": 10, "ಡಿಸೆಂಬರ್": 11,
  };
  
  // Relative day references - each entry is a list of word variants that
  // should all resolve to the same day offset from today.
  const RELATIVE_DATE_WORDS = [
    { offsetDays: 0, words: ["today", "ಇಂದು"] },
    { offsetDays: -1, words: ["yesterday", "ನಿನ್ನೆ"] },
    { offsetDays: -2, words: ["ಮೊನ್ನೆ"] },
  ];
  
  // Words that might get swept up alongside a captured value and should be
  // stripped back off - anchor words themselves, connectors, filler.
  const STOP_WORDS = new Set([
    "is", "was", "in", "at", "the", "a", "my", "i", "am",
    "ಆಗಿದೆ", "ಇದೆ", "ನಲ್ಲಿ", "ನನ್ನ", "ನಾನು",
    "district", "ಜಿಲ್ಲೆ", "village", "ಗ್ರಾಮ", "ಹಳ್ಳಿ", "name", "ಹೆಸರು",
  ]);
  
  const PUNCT_PATTERN = /^[.,;:!?"'()।\u0964\u0965-]+|[.,;:!?"'()।\u0964\u0965-]+$/g;
  const KANNADA_PATTERN = /[\u0C80-\u0CFF]/;
  
  export function extractClaimFields(transcript) {
    try {
      const raw = (transcript || "").trim();
      if (!raw) return {};
  
      const lower = raw.toLowerCase();
      const tokens = tokenize(raw);
      const result = {};
  
      const mobile = findMobileNumber(raw);
      if (mobile) result.mobile_number = mobile;
  
      const name = findValueNearAnchor(tokens, NAME_ANCHORS, "after");
      if (name) result.farmer_name = name;
  
      const crop = findKeywordMatch(tokens, CROP_KEYWORDS);
      if (crop) result.crop_type = crop;
  
      const damage = findKeywordMatch(tokens, DAMAGE_TYPE_KEYWORDS);
      if (damage) result.damage_type = damage;
  
      const district =
        findValueNearAnchor(tokens, DISTRICT_ANCHORS, "before") ||
        findValueNearAnchor(tokens, DISTRICT_ANCHORS, "after");
      if (district) result.district = district;
  
      const village =
        findValueNearAnchor(tokens, VILLAGE_ANCHORS, "before") ||
        findValueNearAnchor(tokens, VILLAGE_ANCHORS, "after");
      if (village) result.village = village;
  
      const date = findDamageDate(raw, lower, tokens);
      if (date) result.damage_date = date;
  
      return result;
    } catch {
      // Extraction must never crash the voice flow - if anything unexpected
      // happens, just fall back to "nothing recognized" and let the farmer
      // fill the form in manually.
      return {};
    }
  }
  
  // ---------------------------------------------------------------------
  // Tokenization & normalization
  // ---------------------------------------------------------------------
  
  function tokenize(raw) {
    return raw
      .split(/\s+/)
      .map(stripPunct)
      .filter(Boolean);
  }
  
  function stripPunct(token) {
    return token.replace(PUNCT_PATTERN, "");
  }
  
  // Kannada has no case; only lowercase ASCII/Latin tokens so English
  // keywords/anchors match regardless of how Whisper capitalized them.
  function normalize(token) {
    return KANNADA_PATTERN.test(token) ? token : token.toLowerCase();
  }
  
  // ---------------------------------------------------------------------
  // Fuzzy matching primitives
  // ---------------------------------------------------------------------
  
  function levenshtein(a, b) {
    if (a === b) return 0;
    if (a.length === 0) return b.length;
    if (b.length === 0) return a.length;
  
    let previousRow = new Array(b.length + 1);
    for (let j = 0; j <= b.length; j++) previousRow[j] = j;
  
    for (let i = 1; i <= a.length; i++) {
      const currentRow = [i];
      for (let j = 1; j <= b.length; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        currentRow[j] = Math.min(
          previousRow[j] + 1, // deletion
          currentRow[j - 1] + 1, // insertion
          previousRow[j - 1] + cost // substitution
        );
      }
      previousRow = currentRow;
    }
  
    return previousRow[b.length];
  }
  
  // Distance budget scales gently with word length, and is deliberately
  // capped so a "match" always stays high-confidence rather than becoming
  // a loose guess on short or very different words.
  function maxAllowedDistance(word) {
    const len = word.length;
    if (len <= 3) return 1;
    if (len <= 7) return 1;
    return 2;
  }
  
  // True if `token` is close enough to `keyword` to count as the same word -
  // covers exact matches, common ASR letter-substitutions (ಹಿಸರು vs ಹೆಸರು),
  // and Kannada suffix attachment (ಜಿಲ್ಲೆಯ / ಗ್ರಾಮದವನು carrying a case
  // ending on top of the root word ಜಿಲ್ಲೆ / ಗ್ರಾಮ).
  function fuzzyTokenMatches(token, keyword) {
    if (!token || !keyword) return false;
    if (token === keyword) return true;
  
    const maxDist = maxAllowedDistance(keyword);
  
    if (levenshtein(token, keyword) <= maxDist) return true;
  
    if (token.length > keyword.length) {
      const prefix = token.slice(0, keyword.length);
      if (levenshtein(prefix, keyword) <= maxDist) return true;
    }
  
    if (token.includes(keyword)) return true;
  
    return false;
  }
  
  // ---------------------------------------------------------------------
  // Phrase location (anchors and multi-word keywords)
  // ---------------------------------------------------------------------
  
  // Finds the first run of adjacent tokens that fuzzily matches every word
  // in `phraseWords`, in order. Returns { start, end } (end is exclusive,
  // i.e. the index right after the phrase) or null if not found.
  function locatePhrase(tokens, phraseWords) {
    const normalizedPhrase = phraseWords.map(normalize);
  
    for (let i = 0; i <= tokens.length - normalizedPhrase.length; i++) {
      let matched = true;
      for (let j = 0; j < normalizedPhrase.length; j++) {
        if (!fuzzyTokenMatches(normalize(tokens[i + j]), normalizedPhrase[j])) {
          matched = false;
          break;
        }
      }
      if (matched) {
        return { start: i, end: i + normalizedPhrase.length };
      }
    }
    return null;
  }
  
  function tokenHasAnyPhrase(tokens, phraseGroups) {
    return phraseGroups.some((phraseWords) => locatePhrase(tokens, phraseWords) !== null);
  }
  
  // ---------------------------------------------------------------------
  // Field extractors
  // ---------------------------------------------------------------------
  
  function findMobileNumber(raw) {
    // Spoken numbers often come through as plain digit runs; scan all
    // digits in the transcript for the first valid 10-digit sequence
    // starting with 6-9 rather than relying on separators.
    const digitsOnly = raw.replace(/\D/g, "");
    for (let i = 0; i <= digitsOnly.length - 10; i++) {
      const candidate = digitsOnly.slice(i, i + 10);
      if (/^[6-9]\d{9}$/.test(candidate)) {
        return candidate;
      }
    }
    return "";
  }
  
  function findKeywordMatch(tokens, entries) {
    for (const entry of entries) {
      for (const keyword of entry.keywords) {
        const phraseWords = keyword.split(/\s+/).filter(Boolean);
        if (locatePhrase(tokens, phraseWords)) {
          return entry.value;
        }
      }
    }
    return "";
  }
  
  // Finds the first matching anchor phrase (tried in priority order) and
  // grabs the tokens immediately before or after it as the field value,
  // stopping at punctuation-only gaps or a recognized stop word.
  function findValueNearAnchor(tokens, anchorGroups, direction) {
    for (const anchorWords of anchorGroups) {
      const location = locatePhrase(tokens, anchorWords);
      if (!location) continue;
  
      const value =
        direction === "after"
          ? collectWords(tokens, location.end, 1, 4)
          : collectWords(tokens, location.start - 1, -1, 4);
  
      if (value) return value;
    }
    return "";
  }
  
  // Walks tokens from `startIndex` in `step` direction (+1 or -1), collecting
  // up to `maxWords` non-stopword tokens, and stops as soon as it hits a
  // stopword after having collected at least one real word.
  function collectWords(tokens, startIndex, step, maxWords) {
    const kept = [];
    let i = startIndex;
  
    while (i >= 0 && i < tokens.length && kept.length < maxWords) {
      const token = tokens[i];
      if (isStopWord(token)) {
        if (kept.length > 0) break;
        i += step;
        continue;
      }
      if (step > 0) kept.push(token);
      else kept.unshift(token);
      i += step;
    }
  
    return kept.join(" ");
  }
  
  function isStopWord(token) {
    return STOP_WORDS.has(normalize(token));
  }
  
  function findDamageDate(raw, lower, tokens) {
    // 1. Explicit numeric dates: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy
    const numeric = raw.match(/\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})\b/);
    if (numeric) {
      const [, day, month, year] = numeric;
      return toIsoDate(year, month, day);
    }
  
    // 2. yyyy-mm-dd (already ISO-ish)
    const iso = raw.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/);
    if (iso) {
      const [, year, month, day] = iso;
      return toIsoDate(year, month, day);
    }
  
    // 3. English month name: "15 july 2026" or "july 15 2026"
    for (let m = 0; m < MONTHS_EN.length; m++) {
      const monthName = MONTHS_EN[m];
      if (!lower.includes(monthName)) continue;
  
      const dayFirst = lower.match(new RegExp(`(\\d{1,2})\\s+${monthName}\\s+(\\d{4})`));
      if (dayFirst) return toIsoDate(dayFirst[2], m + 1, dayFirst[1]);
  
      const monthFirst = lower.match(new RegExp(`${monthName}\\s+(\\d{1,2})\\s+(\\d{4})`));
      if (monthFirst) return toIsoDate(monthFirst[2], m + 1, monthFirst[1]);
    }
  
    // 4. Kannada month name, e.g. "15 ಜುಲೈ 2026"
    for (const [monthName, monthIndex] of Object.entries(MONTHS_KN)) {
      if (!raw.includes(monthName)) continue;
      const match = raw.match(new RegExp(`(\\d{1,2})\\s*${monthName}\\s*(\\d{4})`));
      if (match) return toIsoDate(match[2], monthIndex + 1, match[1]);
    }
  
    // 5. Relative day words - ಇಂದು (today), ನಿನ್ನೆ (yesterday),
    //    ಮೊನ್ನೆ (day before yesterday) - fuzzy-matched so small ASR
    //    misspellings of these common words still resolve.
    for (const { offsetDays, words } of RELATIVE_DATE_WORDS) {
      if (tokenHasAnyPhrase(tokens, words.map((w) => [w]))) {
        const date = new Date();
        date.setDate(date.getDate() + offsetDays);
        return date.toISOString().split("T")[0];
      }
    }
  
    return "";
  }
  
  function toIsoDate(year, month, day) {
    const y = String(year).padStart(4, "0");
    const m = String(month).padStart(2, "0");
    const d = String(day).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }