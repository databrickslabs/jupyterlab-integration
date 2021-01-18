from dataclasses import dataclass
from datetime import datetime
from difflib import ndiff
from typing import List, Dict
import re


@dataclass
class Comment:
    indent: str
    value: str

    def to_string(self):
        return f"{self.indent}{self.value}"


@dataclass
class KeyValue:
    indent: str
    key: str
    sep: str
    value: str
    comment: str

    def to_string(self):
        return f"{self.indent}{self.key}{self.sep}{self.value}{self.comment}"


@dataclass
class Block:
    head: KeyValue
    params: List[KeyValue]
    indent: str = ""
    tag: str = ""

    def to_string(self):
        return f"{self.head.to_string()}\n" + "\n".join([p.to_string() for p in self.params])

    def get_param(self, key):
        for kv in self.params:
            if isinstance(kv, KeyValue) and kv.key.lower() == key.lower():
                return kv
        return None

    def set_param(self, key, value):
        p = self.get_param(key)
        if p is None:
            if self.params and self.params[-1].value == "":
                self.params.insert(
                    len(self.params) - 1,
                    KeyValue(self.indent, key, " ", value, self.tag),
                )
            else:
                self.params.append(KeyValue(self.indent, key, " ", value, self.tag))
        else:
            p.value = value
            if self.tag != "" and not self.tag in p.comment:
                p.comment += self.tag
        return self


@dataclass
class SshConfig:
    data: str
    tag: str = ""
    blocks: List = None

    def __post_init__(self):
        self.parse()

    def to_string(self):
        return "\n".join([b.to_string() for b in self.blocks])

    @staticmethod
    def parse_line(raw_line):
        indent, line = re.match("(^\s*)(.*)", raw_line).groups()
        definition = re.split(r"(\s*#[#\s]+)", line)
        comment = "" if len(definition) == 1 else "".join(definition[1:])
        key_values = definition[0]

        values = re.split(r"([=\s]+)", key_values)
        key = values[0]
        sep = "" if len(values) == 1 else values[1]
        value = "" if len(values) == 1 else "".join(values[2:])
        return [indent, key, sep, value, comment]

    def parse(self):
        self.blocks = []
        lines = self.data.split("\n")
        block = None
        for line in lines:
            indent, key, sep, params, comment = self.parse_line(line)
            if key == "" and comment == "":
                if block is None:
                    self.blocks.append(Comment("", ""))
                else:
                    block.params.append(Comment("", ""))
            elif key == "" and comment != "" and block is None:
                self.blocks.append(Comment(indent, comment))
            elif key.lower() in ["host", "match"]:
                if block is not None:
                    self.blocks.append(block)
                    block = None
                head = KeyValue(indent, key, sep, params, comment)
                block = Block(head, [], tag=self.tag)
            else:
                block.params.append(KeyValue(indent, key, sep, params, comment))
                if key != "":
                    block.indent = indent

        if block is not None:
            self.blocks.append(block)
        return self

    def get_host(self, name):
        for b in self.blocks:
            if isinstance(b, Block) and "".join(b.head.value) == name:
                return b
        return None

    def add_host(self, host):
        block = self.get_host(host)
        if block is None:
            block = Block(
                KeyValue("", "Host", " ", host, ""),
                [],
                "    ",
                tag=self.tag,
            )
            self.blocks.append(block)
        return block

    def dump(self):
        print("\n".join(ndiff(self.data.split("\n"), self.to_string().split("\n"))))