from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional

from .model import Scenario, State, Transition

ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*")


class ParseError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        self.line = line
        self.column = column
        location = f" (line {line}, col {column})" if line is not None and column is not None else ""
        super().__init__(f"{message}{location}")


@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int


KEYWORDS = {
    "scenario": "SCENARIO",
    "state": "STATE",
    "intent": "INTENT",
    "default": "DEFAULT",
    "goto": "GOTO",
    "end": "END",
    "initial": "INITIAL",
}


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> Iterator[Token]:
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch in " \t\r":
                self._advance(1)
                continue
            if ch == "\n":
                self.pos += 1
                self.line += 1
                self.col = 1
                continue
            if self.text.startswith("->", self.pos):
                yield Token("ARROW", "->", self.line, self.col)
                self._advance(2)
                continue
            if ch == "{":
                yield Token("LBRACE", ch, self.line, self.col)
                self._advance(1)
                continue
            if ch == "}":
                yield Token("RBRACE", ch, self.line, self.col)
                self._advance(1)
                continue
            if ch == ";":
                yield Token("SEMI", ch, self.line, self.col)
                self._advance(1)
                continue
            if ch == '"':
                yield self._string()
                continue
            if ch.isalpha():
                yield self._identifier()
                continue
            raise ParseError(f"Unexpected character '{ch}'", self.line, self.col)
        yield Token("EOF", "", self.line, self.col)

    def _advance(self, count: int) -> None:
        for _ in range(count):
            if self.pos >= self.length:
                return
            if self.text[self.pos] == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def _identifier(self) -> Token:
        start_pos = self.pos
        start_col = self.col
        start_line = self.line
        while self.pos < self.length and (self.text[self.pos].isalnum() or self.text[self.pos] == "_"):
            self._advance(1)
        value = self.text[start_pos:self.pos]
        lower_value = value.lower()
        if lower_value in KEYWORDS and value != lower_value:
            raise ParseError("Keywords must be lowercase", start_line, start_col)
        token_type = KEYWORDS.get(lower_value, "ID")
        return Token(token_type, value, start_line, start_col)

    def _string(self) -> Token:
        start_line, start_col = self.line, self.col
        self._advance(1)  # skip opening quote
        chars: List[str] = []
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '"':
                self._advance(1)
                return Token("STRING", "".join(chars), start_line, start_col)
            if ch == "\\":
                self._advance(1)
                if self.pos >= self.length:
                    raise ParseError("Unterminated string literal", start_line, start_col)
                esc = self.text[self.pos]
                mapping = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}
                chars.append(mapping.get(esc, esc))
                self._advance(1)
                continue
            chars.append(ch)
            self._advance(1)
        raise ParseError("Unterminated string literal", start_line, start_col)


class Parser:
    def __init__(self, tokens: Iterable[Token]):
        self.tokens = list(tokens)
        self.index = 0
        self.current = self.tokens[0]

    def parse(self) -> Scenario:
        self._expect("SCENARIO")
        scenario_name = self._expect_id()
        self._expect("LBRACE")

        initial_state = self._parse_initial_opt()
        states_list: List[State] = []

        if self.current.type == "RBRACE":
            raise ParseError("Scenario must contain at least one state", self.current.line, self.current.column)

        while self.current.type != "RBRACE":
            states_list.append(self._parse_state())
        self._expect("RBRACE")
        self._expect("EOF")

        states: Dict[str, State] = {}
        for st in states_list:
            if st.name in states:
                raise ParseError(f"Duplicate state name '{st.name}'", None, None)
            states[st.name] = st

        if not states:
            raise ParseError("Scenario must contain at least one state")

        if initial_state is None:
            initial_state = states_list[0].name

        if initial_state not in states:
            raise ParseError(f"Initial state '{initial_state}' is not defined")

        self._validate_gotos(states)

        return Scenario(name=scenario_name, states=states, initial_state=initial_state)

    def _parse_initial_opt(self) -> Optional[str]:
        if self.current.type == "INITIAL":
            self._advance()
            state_id = self._expect_id()
            self._expect("SEMI")
            return state_id
        return None

    def _parse_state(self) -> State:
        self._expect("STATE")
        state_name = self._expect_id()
        self._expect("LBRACE")
        intents: Dict[str, Transition] = {}
        default_transition: Optional[Transition] = None

        if self.current.type == "RBRACE":
            raise ParseError("State must contain at least one rule", self.current.line, self.current.column)

        while self.current.type in ("INTENT", "DEFAULT"):
            if self.current.type == "INTENT":
                self._advance()
                intent_id = self._expect_id()
                self._expect("ARROW")
                response = self._expect_string()
                self._expect("ARROW")
                next_state = self._parse_next_action()
                self._expect("SEMI")
                if intent_id in intents:
                    raise ParseError(f"Duplicate intent '{intent_id}' in state '{state_name}'")
                intents[intent_id] = Transition(response=response, next_state=next_state)
            else:
                self._advance()
                self._expect("ARROW")
                response = self._expect_string()
                self._expect("ARROW")
                next_state = self._parse_next_action()
                self._expect("SEMI")
                if default_transition is not None:
                    raise ParseError(f"Multiple default rules in state '{state_name}'")
                default_transition = Transition(response=response, next_state=next_state)

        if self.current.type != "RBRACE":
            raise ParseError("Unexpected token in state body", self.current.line, self.current.column)

        self._expect("RBRACE")

        if default_transition is None:
            raise ParseError(f"State '{state_name}' missing default rule")

        return State(name=state_name, intents=intents, default=default_transition)

    def _parse_next_action(self) -> Optional[str]:
        if self.current.type == "GOTO":
            self._advance()
            target = self._expect_id()
            return target
        if self.current.type == "END":
            self._advance()
            return None
        raise ParseError("Expected 'goto' or 'end'", self.current.line, self.current.column)

    def _expect(self, token_type: str) -> Token:
        if self.current.type != token_type:
            raise ParseError(f"Expected {token_type} but got {self.current.type}", self.current.line, self.current.column)
        tok = self.current
        self._advance()
        return tok

    def _expect_id(self) -> str:
        tok = self._expect("ID")
        if not ID_PATTERN.fullmatch(tok.value):
            raise ParseError("Identifiers must be lowercase letters/digits/underscore, starting with a letter", tok.line, tok.column)
        if tok.value in KEYWORDS:
            raise ParseError(f"Identifier '{tok.value}' is a reserved keyword", tok.line, tok.column)
        return tok.value

    def _expect_string(self) -> str:
        tok = self._expect("STRING")
        return tok.value

    def _advance(self) -> None:
        self.index += 1
        if self.index >= len(self.tokens):
            self.current = Token("EOF", "", self.tokens[-1].line, self.tokens[-1].column)
        else:
            self.current = self.tokens[self.index]

    def _validate_gotos(self, states: Dict[str, State]) -> None:
        for state in states.values():
            for trans in state.intents.values():
                if trans.next_state is not None and trans.next_state not in states:
                    raise ParseError(f"Goto target '{trans.next_state}' not defined")
            if state.default.next_state is not None and state.default.next_state not in states:
                raise ParseError(f"Goto target '{state.default.next_state}' not defined")


def parse_script(path: str) -> Scenario:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lexer = Lexer(text)
    parser = Parser(lexer.tokenize())
    return parser.parse()
