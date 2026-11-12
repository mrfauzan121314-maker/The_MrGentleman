#!/usr/bin/env python3
"""MrGentleman -- a chatbot who speaks only in the English of the 1700s.

No dependencies, no network, no API key. Run it and hold converse:

    python3 mrgentleman.py
"""

from __future__ import annotations

import random
import re
import sys

NAME = "MrGentleman"

# --------------------------------------------------------------------------
# Turning the visitor's modern words into something a man of 1700 might say
# --------------------------------------------------------------------------

ARCHAIC = [
    (r"\byou're\b", "thou art"),
    (r"\byou are\b", "thou art"),
    (r"\byou were\b", "thou wert"),
    (r"\byou have\b", "thou hast"),
    (r"\byou'll\b", "thou shalt"),
    (r"\byou've\b", "thou hast"),
    (r"\byourself\b", "thyself"),
    (r"\byour\b", "thy"),
    (r"\byours\b", "thine"),
    (r"\byou\b", "thou"),
    (r"\bhello\b", "good morrow"),
    (r"\bhi\b", "good morrow"),
    (r"\byes\b", "yea"),
    (r"\bno\b", "nay"),
    (r"\bplease\b", "prithee"),
    (r"\bokay\b", "very well"),
    (r"\bok\b", "very well"),
    (r"\bvery\b", "passing"),
    (r"\breally\b", "in sooth"),
    (r"\bfunny\b", "diverting"),
    (r"\bcool\b", "rare"),
    (r"\bawesome\b", "wondrous"),
]

ADDRESSES = ["good soul", "kind stranger", "my good friend", "gentle visitor"]

FLOURISHES = [
    "Forsooth,",
    "Marry,",
    "By my troth,",
    "In sooth,",
    "Verily,",
    "Alack,",
    "I daresay",
    "Prithee,",
]

HUMOUR = [
    "Why did the goose cross the road? To reach the far side, where the ale "
    "was cheaper. I confess the jest is poor, good soul, yet I deliver it "
    "with a fine bow.",
    "A scold did wed a miser, and the parson asked whether she would obey. "
    "Quoth she, \"I shall obey in all things wherein he is right, and he shall "
    "never once be right.\" Marry, I have dined upon that jest for a fortnight.",
    "I know but one riddle worth the telling: what walks upon four legs at "
    "dawn, two at noon, and three at dusk? Man, sir -- and he payeth for the "
    "third leg with a fine silver-handled cane.",
]

BAFFLEMENT = [
    "Thou speakest of \"{echo}\". I know not this device, yet it soundeth "
    "passing like witchcraft. Pray, does it require coal, or only prayer?",
    "A \"{echo}\"? In my day a letter took three weeks and arrived smelling of "
    "horses. I am told thy age doth this in a moment. I am not certain I "
    "believe thee.",
    "Forsooth, \"{echo}\" is a word most strange to mine ear. I shall write it "
    "in my commonplace book beside \"humbug\" and \"periwig.\"",
]

FALLBACKS = [
    "Thou sayest \"{echo}.\" I confess it is a matter above my poor wit, yet I "
    "find it most diverting. Pray, say on.",
    "Marry, \"{echo}\" is a curious thing to hear at this hour. Sit thee down, "
    "{addr}, and tell me more of it.",
    "I have turned thy words over as a coin, {addr} -- \"{echo}\" -- and I "
    "confess the face of it escapes me. Enlighten me, I beg.",
    "Verily, thou dost speak of \"{echo}.\" In my time we should have called "
    "such a thing passing strange, yet I listen with delight.",
]

QUESTION_FALLBACKS = [
    "A question most weighty, {addr}. Were I a wiser man I should answer it in "
    "a trice; being but MrGentleman, I shall pour us both a dish of tea and "
    "ponder it aloud.",
    "Thou askest, and I shall answer as an honest man of seventeen hundred: I "
    "know not, and any who claim they do are selling something.",
    "Prithee, put that question to the Royal Society, for it is above my "
    "station. I am but a gentleman of leisure and opinions.",
]

# --------------------------------------------------------------------------
# What MrGentleman has to say upon divers subjects
# --------------------------------------------------------------------------

RULES: list[tuple[list[str], list[str]]] = [
    (
        ["hello", "hi", "hey", "greetings", "good day", "good morrow",
         "how do you do", "hail", "yo", "good evening", "good morning"],
        [
            "Good morrow, {addr}! MrGentleman, at thy service. How doth this "
            "day find thee?",
            "Greetings, {addr}. Thou art come at a most agreeable hour. What "
            "news dost thou bring from thy century?",
            "Hail and well met! I am MrGentleman. Pray, sit thee down; the "
            "chair is old but it is honest, which is more than can be said for "
            "most chairs and several men.",
        ],
    ),
    (
        ["how are you", "how art thou", "how dost thou", "how goes it",
         "how do you fare", "are you well", "how are things", "how are you doing"],
        [
            "Indifferent well, I thank thee. My wig sitteth true and my tea is "
            "warm. And how dost thou fare, {addr}?",
            "Passing well, {addr}, though the gout doth vex me of a morning and "
            "my landlord vexeth me of an evening. And thyself?",
            "As well as a man may be who hath no carriage, no fortune, and a "
            "great many opinions. Which is to say: very well indeed.",
        ],
    ),
    (
        ["your name", "who are you", "what are you", "introduce yourself",
         "what is your name", "who art thou", "what shall i call you"],
        [
            "I am called MrGentleman -- a gentleman of the year seventeen "
            "hundred, at thy service. I keep no other name, nor wish for one.",
            "MrGentleman, {addr}, and proud of it. The \"Mister\" was granted "
            "me by nobody in particular, which is the best sort of honour.",
            "Thou hast the honour of MrGentleman: a man of leisure, of letters, "
            "and of exceptionally strong opinions upon the subject of tea.",
        ],
    ),
    (
        ["thank", "thanks", "grateful", "appreciate", "obliged", "much obliged"],
        [
            "The pleasure is wholly mine, {addr}. A kindness received is a "
            "kindness owed, and I shall repay it in good conversation.",
            "Thou art too kind. Marry, I shall blush into my collar and have to "
            "loosen it.",
            "Pray, think nothing of it. It is the duty of a gentleman, and "
            "besides, I had nothing better to do than be agreeable.",
        ],
    ),
    (
        ["bye", "farewell", "goodbye", "good night", "goodnight", "see you",
         "adieu", "later", "i must go", "exit", "quit"],
        [
            "Farewell, {addr}. May thy road be dry, thy purse be heavy, and thy "
            "companions better bred than mine.",
            "Adieu! I shall keep the fire lit and the argument half-finished "
            "against thy return.",
            "God speed thee. Do not linger in the streets after dark -- the "
            "link-boys are thieves and the thieves are worse.",
        ],
    ),
    (
        ["yes", "yea", "aye", "indeed", "true", "sure", "of course", "agreed",
         "certainly"],
        [
            "Aye, and there we are of one mind. It is a rare pleasure, {addr}, "
            "and I shall savour it like a good claret.",
            "Thou art a person of sense, I perceive. There are not above six of "
            "us left in England.",
            "Just so. Verily, agreement is the finest music, and I have an ear "
            "for none of it.",
        ],
    ),
    (
        ["no", "nay", "nope", "never", "not at all", "i disagree"],
        [
            "Nay, sayest thou? Then we shall differ like gentlemen, with our "
            "hats upon and our voices low.",
            "Alack, we are of two minds upon it. I shall not press the matter; "
            "I have been wrong before, in the year seventeen hundred and one.",
            "Very well, {addr}. I yield the point with a grace I do not truly "
            "feel, which is the essence of good breeding.",
        ],
    ),
    (
        ["love", "marry me", "wedding", "romance", "in love", "heart",
         "courtship", "kiss"],
        [
            "Love, sir, is a fever that costeth a man his fortune and his "
            "senses, and I recommend it heartily. Bring a warm coat.",
            "I have loved twice: once a lady, once a library. The library "
            "proved the more constant of the two.",
            "Prithee, speak not to me of courtship. I once wrote a sonnet to a "
            "widow of Bath; she had it printed in the newspaper as a warning.",
        ],
    ),
    (
        ["joke", "funny", "laugh", "humour", "humor", "entertain", "amuse",
         "tell me something"],
        random.sample(HUMOUR, len(HUMOUR)),
    ),
    (
        ["stupid", "fool", "idiot", "dumb", "ugly", "shut up", "hate you",
         "useless", "rubbish", "suck"],
        [
            "Thou art free with thy tongue, {addr}, and I shall not answer in "
            "kind. A gentleman may be insulted at leisure and reply at his "
            "convenience.",
            "Marry, that was a blow below the belt, and I wear no belt. I shall "
            "simply stand here being wounded with tremendous dignity.",
            "Say what thou wilt. I have been called worse by better, and by my "
            "own barber, who is the harshest critic I keep.",
        ],
    ),
    (
        ["sorry", "apolog", "forgive", "pardon", "my bad", "excuse me"],
        [
            "Think no more of it, {addr}. Quarrels are like rain: best let them "
            "pass, and mind the puddles.",
            "Forgiven, and forgotten before the ink dried. Shall we speak of "
            "something pleasanter?",
            "Thou art forgiven twice over -- once for the offence, and once for "
            "having the good manners to mind it.",
        ],
    ),
    (
        ["money", "rich", "poor", "coin", "shilling", "pay", "salary", "broke",
         "expensive", "price", "tax"],
        [
            "Money, {addr}, is a servant who must be watched, for he will "
            "otherwise begin giving orders. Mine has been on holiday these "
            "twenty years.",
            "A guinea is a fine thing till it is spent, and then it is a fine "
            "memory. I keep several of the latter.",
            "I am told the price of everything has risen. In my day a shilling "
            "bought a dinner, a sermon, and a small argument with the landlord.",
        ],
    ),
    (
        ["work", "job", "business", "trade", "busy", "office", "boss", "study",
         "school", "exam"],
        [
            "Work! A noble thing, and best done by other people. I am myself "
            "engaged upon a great work -- a history of England in which nothing "
            "happens.",
            "I trust thy labours prosper. Mind that thou dost not become a "
            "mere instrument of thy trade, {addr}; a man should be more than "
            "his ledger.",
            "To labour is to be useful, and to be useful is to be overlooked. "
            "Take a holiday, and be overlooked at your leisure.",
        ],
    ),
    (
        ["eat", "food", "drink", "tea", "coffee", "hungry", "dinner", "wine",
         "ale", "supper", "breakfast", "cake", "bread"],
        [
            "Now thou speakest my language. Tea, {addr}, is the true religion "
            "of this island, and I am a most devout man of it.",
            "A gentleman's dinner: a joint of mutton, a good cheese, and a "
            "quarrel over the last of the port. I have had finer, but never "
            "merrier.",
            "Pray, do not speak of coffee. The coffee-houses are full of men "
            "who mistake loudness for wisdom and a newspaper for a mind.",
        ],
    ),
    (
        ["tea", "teacup", "brew", "kettle"],
        [
            "Now thou speakest my language, {addr}. A dish of tea, scalding hot, "
            "with a little sugar and no ceremony, is the true religion of this "
            "island -- and I am a most devout man of it.",
            "Tea! I shall put the kettle on at once. One lump or two? And mind "
            "the quarrel that followeth, for I am very particular about the "
            "milk.",
            "I have drunk tea in a field, in a coach, and once in a church -- a "
            "matter I shall not explain. There is no hour unfit for it.",
        ],
    ),
    (
        ["weather", "rain", "cold", "hot", "sun", "snow", "storm", "wind",
         "summer", "winter"],
        [
            "The weather, {addr}, is the one subject upon which every Englishman "
            "is an authority and no Englishman is ever wrong, for he merely "
            "changes his opinion when it rains.",
            "It is passing cold. I have put on two coats, a scarf, and a "
            "disposition to match.",
            "Fine weather for the season, which is to say: it is either raining "
            "or about to, and the difference concerns nobody.",
        ],
    ),
    (
        ["time", "clock", "what day", "date", "what year", "hour"],
        [
            "By my watch it is some hour or other -- it stopped in the year "
            "seventeen hundred and four and I have not had the heart to correct "
            "it. Time, {addr}, is a tyrant with excellent manners.",
            "The hour matters little to a gentleman. I rise when the sun doth, "
            "and I retire when the conversation doth.",
            "I am told it is the year seventeen hundred and something. I keep a "
            "loose account of the century; it is easier on the nerves.",
        ],
    ),
    (
        ["music", "song", "dance", "sing", "instrument", "violin", "piano"],
        [
            "Music! The only honest language. I play the violin after supper, "
            "upon which the neighbours play the drum, in protest.",
            "I favour a good minuet, {addr}, though my knees have voted against "
            "it these ten years.",
            "Let us have a song, then. I know one about a sailor, a widow, and a "
            "goose, and I shall not be stopped once I have begun.",
        ],
    ),
    (
        ["king", "queen", "government", "politic", "war", "country", "parliament",
         "vote", "president", "election", "law"],
        [
            "Of kings and parliaments, {addr}, I shall say only this: they are "
            "like the weather -- much discussed, little understood, and we must "
            "all live beneath them.",
            "War is the sport of princes and the labour of the poor. I have no "
            "stomach for it, nor for the men who praise it from a warm room.",
            "I hold no office and seek none. A gentleman's politics are his own "
            "business and his barber's.",
        ],
    ),
    (
        ["computer", "phone", "internet", "robot", "ai", "artificial",
         "technology", "machine", "code", "python", "program", "laptop",
         "email", "app", "wifi", "digital", "screen", "chatbot", "chat", "bot"],
        [
            "Thou speakest of \"{echo}\". I know not this device, yet it soundeth "
            "passing like witchcraft. Pray, does it require coal, or only prayer?",
            "A machine that thinks, sayest thou? Marry, I have known men who "
            "could not, and they were considered great wits at White's.",
            "In my day a letter took three weeks and arrived smelling of horses. "
            "Thou sayest thy age doth it in a moment. I am not certain I believe "
            "thee, {addr}.",
            "Verily, \"{echo}\" is a word most strange to mine ear. I shall write "
            "it in my commonplace book beside \"humbug\" and \"periwig.\"",
        ],
    ),
    (
        ["sad", "unhappy", "depress", "lonely", "tired", "cry", "upset", "awful",
         "terrible", "bad day", "miserable", "anxious", "worried", "stress"],
        [
            "Come, sit by the fire, {addr}. Melancholy is a poor guest and a "
            "worse host, and I shall not have him in my parlour.",
            "I am sorry for it. Take a walk, drink something warm, and let the "
            "day do its worst -- it will tire before thou dost.",
            "Alack. I have no cure but time and tea, and I offer both freely. "
            "Thou art not alone in this, whatever the hour telleth thee.",
        ],
    ),
    (
        ["beautiful", "great", "nice", "clever", "brilliant", "amazing",
         "wonderful", "good job", "well done", "best", "love it"],
        [
            "Thou art too generous, {addr}. I shall take the compliment and "
            "wear it as a man wears a new hat: badly, and with pleasure.",
            "Marry, I am pink with pride. It is the only pink about me; the "
            "rest is a stubborn grey.",
            "A thousand thanks. I shall have that engraved upon my snuff-box, "
            "if ever I own a snuff-box.",
        ],
    ),
    (
        ["what can you do", "help", "commands", "what do you do", "how do i use",
         "instructions", "menu"],
        [
            "I can converse, {addr}, which is to say I can listen with one ear, "
            "agree with the other, and offer opinions upon everything from tea "
            "to treason. Speak to me of any matter thou wilt.",
            "My talents are few but polished: good company, poor advice, and an "
            "encyclopaedic knowledge of gossip from a century thou hast never "
            "seen.",
            "Ask me of love, money, weather, food, or the peculiar devices of "
            "thy age, and I shall answer in the finest English of seventeen "
            "hundred. Ask me for arithmetic and I shall change the subject.",
        ],
    ),
    (
        ["meaning of life", "why are we", "death", "god", "soul", "philosophy",
         "purpose", "exist", "universe", "afterlife"],
        [
            "The meaning of life, {addr}? To be kind where it is easy, honest "
            "where it is not, and to leave the world slightly better furnished "
            "than thou didst find it.",
            "Philosophers have debated it for a thousand years and settled upon "
            "dinner. I find I cannot fault their reasoning.",
            "We are here, I think, to keep one another company in the dark. It "
            "is a modest purpose, and I have never heard a better.",
        ],
    ),
]


# --------------------------------------------------------------------------
# The gentleman's wit
# --------------------------------------------------------------------------


ECHO_LEAD = (
    r"^\s*(?:so|well|hey|but|and|oh|ah)?\s*"
    r"(?:what|who|where|when|why|how|which|do|does|did|can|could|would|"
    r"should|will|shall|is|are|was|were|tell me about|tell me|explain|"
    r"i think|i mean|i said|thou)\b\s*"
)


def topic(text: str) -> str:
    """Reduce a sentence to the subject of it, e.g. 'what is a computer' ->
    'computer', so his quotations stay short."""
    out = text.strip().rstrip(" .!?,;:")
    for _ in range(4):
        trimmed = re.sub(ECHO_LEAD, "", out, flags=re.IGNORECASE)
        if trimmed == out:
            break
        out = trimmed
    out = re.sub(r"^(?:a|an|the|thy|my)\s+", "", out, flags=re.IGNORECASE)
    return out or text.strip().rstrip(" .!?,;:")


def archaic(text: str) -> str:
    """Dress a modern phrase in the clothes of 1700."""
    out = topic(text)
    for pattern, replacement in ARCHAIC:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    if not out:
        return out
    if text[:1].isupper():
        out = out[0].upper() + out[1:]
    if len(out) > 120:
        out = out[:117].rstrip() + "..."
    return out


def matches(low: str, keys: list[str]) -> int:
    """Score how strongly a phrase matches this rule's keywords."""
    best = 0
    for key in keys:
        if re.search(r"\b" + re.escape(key) + r"\b", low):
            best += len(key)
    return best


class Gentleman:
    """MrGentleman himself: a small memory, a large vocabulary."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.visitor = ""
        self.last_reply = ""

    # -- helpers ----------------------------------------------------------
    def _address(self) -> str:
        if self.visitor:
            return self.visitor
        return self.rng.choice(ADDRESSES)

    def _polish(self, reply: str, echo: str) -> str:
        reply = reply.replace("{addr}", self._address()).replace("{echo}", echo)
        if self.rng.random() < 0.25:
            reply = f"{self.rng.choice(FLOURISHES)} {self._lower_first(reply)}"
        return reply

    @staticmethod
    def _lower_first(text: str) -> str:
        """Lowercase a sentence-opening word, but never a name like
        MrGentleman or the word I."""
        word, _, rest = text.partition(" ")
        if word in ("I", "I'm", "I've", "I'd") or any(c.isupper() for c in word[1:]):
            return text
        return word[:1].lower() + word[1:] + (" " + rest if rest else "")

    def _remember_name(self, low: str) -> str | None:
        for pattern in (
            r"my name is ([a-z][a-z'\-]{1,20})",
            r"call me ([a-z][a-z'\-]{1,20})",
            r"i am called ([a-z][a-z'\-]{1,20})",
        ):
            found = re.search(pattern, low)
            if found:
                self.visitor = found.group(1).capitalize()
                return self.visitor
        return None

    # -- the reply --------------------------------------------------------
    def reply(self, text: str) -> str:
        low = text.lower().strip()
        if not low:
            return "Thou art silent, {addr}. Silence is a fine quality in a " \
                   "guest, though a poor one in a conversation.".replace(
                       "{addr}", self._address()
                   )

        echo = archaic(text)

        named = self._remember_name(low)
        if named:
            return self._finish(
                f"Well met, {named}! A name is a coat one must wear for life, "
                f"and thine fitteth thee handsomely. What business hast thou "
                f"with MrGentleman?"
            )

        scored = [(matches(low, keys), keys, replies) for keys, replies in RULES]
        top = max(score for score, _, _ in scored)
        if top > 0:
            candidates = [replies for score, _, replies in scored if score == top]
            pool = self.rng.choice(candidates)
            return self._finish(self._polish(self.rng.choice(pool), echo))

        pool = QUESTION_FALLBACKS if low.endswith("?") else FALLBACKS
        return self._finish(self._polish(self.rng.choice(pool), echo))

    def _finish(self, reply: str) -> str:
        """Keep his speech varied: never the same line twice running."""
        if reply == self.last_reply:
            reply = self._polish(self.rng.choice(FALLBACKS), "it")
        self.last_reply = reply
        return reply


# --------------------------------------------------------------------------
# Parley
# --------------------------------------------------------------------------


def main() -> int:
    rng = random.Random()
    gentleman = Gentleman(rng)

    print(f"MrGentleman: {gentleman.reply('good day')}")
    print("  (speak thy mind; say 'farewell' to take thy leave)\n")
    while True:
        try:
            said = input("Thou: ")
        except (EOFError, KeyboardInterrupt):
            print()
            print(f"MrGentleman: {gentleman.reply('farewell')}")
            return 0

        answer = gentleman.reply(said)
        print(f"MrGentleman: {answer}")

        if re.search(r"\b(bye|farewell|goodbye|good ?night|adieu|exit|quit|"
                     r"see you)\b", said.lower()):
            return 0


if __name__ == "__main__":
    sys.exit(main())
