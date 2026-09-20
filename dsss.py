#!/usr/bin/env python3
"""Parse decrypted RE Engine DSSS class payloads and emit a flat JSON record list."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path


TYPE_NAMES = {
    -1: "Array",
    0: "Unknown",
    1: "Enum",
    2: "Boolean",
    3: "S8",
    4: "U8",
    5: "S16",
    6: "U16",
    7: "S32",
    8: "U32",
    9: "S64",
    10: "U64",
    11: "F32",
    12: "F64",
    13: "C8",
    14: "C16",
    15: "String",
    16: "Struct",
    17: "Class",
}


@dataclass
class Reader:
    data: bytes
    pos: int = 0

    def need(self, count: int) -> None:
        if count < 0 or self.pos + count > len(self.data):
            raise EOFError(f"need {count} bytes at 0x{self.pos:X}, length=0x{len(self.data):X}")

    def read(self, count: int) -> bytes:
        self.need(count)
        out = self.data[self.pos : self.pos + count]
        self.pos += count
        return out

    def unpack(self, fmt: str):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(size))[0]

    def u32(self) -> int:
        return self.unpack("<I")

    def i32(self) -> int:
        return self.unpack("<i")

    def align(self, size: int) -> None:
        if size not in (1, 2, 4, 8, 16, 32):
            raise ValueError("unsupported alignment")
        if size > 1:
            self.pos = (self.pos + size - 1) & ~(size - 1)


def parse_sized(r: Reader, field_type: int, size: int, path: str, records: list[dict]):
    r.align(size)
    offset = r.pos
    fmts = {
        1: {1: "<b", 2: "<h", 4: "<i", 8: "<q"}.get(size),
        2: "<?",
        3: "<b",
        4: "<B",
        5: "<h",
        6: "<H",
        7: "<i",
        8: "<I",
        9: "<q",
        10: "<Q",
        11: "<f",
        12: "<d",
        13: "<B",
        14: "<H",
    }
    if field_type == 16:
        raw = r.read(size)
        value = raw.hex() if size <= 32 else raw[:32].hex() + "..."
    else:
        fmt = fmts.get(field_type)
        if fmt is None or struct.calcsize(fmt) != size:
            raise ValueError(f"invalid sized type={field_type} size={size} at 0x{offset:X}")
        value = r.unpack(fmt)
    records.append({
        "path": path,
        "type": TYPE_NAMES[field_type],
        "offset": offset,
        "size": size,
        "value": value,
    })


def parse_array(r: Reader, path: str, records: list[dict]) -> None:
    r.align(4)
    header_offset = r.pos
    member_type = r.i32()
    member_size = r.u32()
    length = r.u32()
    array_type = r.i32()
    if member_type not in TYPE_NAMES or array_type not in (0, 1) or length > 100_000:
        raise ValueError(f"bad array header at 0x{header_offset:X}")
    records.append({
        "path": path,
        "type": "ArrayMeta",
        "offset": header_offset,
        "member_type": TYPE_NAMES[member_type],
        "member_size": member_size,
        "length": length,
        "array_type": "Class" if array_type else "Value",
    })
    hashes = None
    if array_type == 1:
        marker_pos = r.pos
        marker = r.u32()
        if marker == 0xFFEEFFEE:
            hashes = [r.u32() for _ in range(length)]
        else:
            r.pos = marker_pos
    for i in range(length):
        item_path = f"{path}[{i}]"
        if array_type == 1:
            parse_class(r, item_path, records, expected_hash=None if hashes is None else hashes[i])
        elif member_type == 15:
            r.align(4)
            off = r.pos
            count = r.u32()
            raw = r.read(count * 2)
            records.append({"path": item_path, "type": "String", "offset": off, "size": count * 2, "value": raw.decode("utf-16-le", errors="replace")})
        else:
            parse_sized(r, member_type, member_size, item_path, records)
    r.align(4)


def parse_value(r: Reader, field_type: int, path: str, records: list[dict]) -> None:
    if field_type == -1:
        parse_array(r, path, records)
    elif field_type == 17:
        parse_class(r, path, records)
    elif field_type == 15:
        r.align(4)
        off = r.pos
        count = r.u32()
        raw = r.read(count * 2)
        records.append({"path": path, "type": "String", "offset": off, "size": count * 2, "value": raw.decode("utf-16-le", errors="replace")})
    else:
        r.align(4)
        size = r.u32()
        parse_sized(r, field_type, size, path, records)


def parse_class(r: Reader, path: str, records: list[dict], expected_hash: int | None = None) -> None:
    class_offset = r.pos
    field_count = r.u32()
    class_hash = r.u32()
    if field_count > 10_000:
        raise ValueError(f"bad class field count at 0x{class_offset:X}")
    records.append({
        "path": path,
        "type": "ClassMeta",
        "offset": class_offset,
        "class_hash": f"{class_hash:08X}",
        "expected_hash": None if expected_hash is None else f"{expected_hash:08X}",
        "field_count": field_count,
    })
    for index in range(field_count):
        field_offset = r.pos
        field_hash = r.u32()
        field_type = r.i32()
        if field_type not in TYPE_NAMES:
            raise ValueError(f"unknown field type {field_type} at 0x{field_offset:X}")
        field_path = f"{path}/f{index}:{field_hash:08X}"
        before = len(records)
        parse_value(r, field_type, field_path, records)
        for rec in records[before:]:
            rec.setdefault("field_hash", f"{field_hash:08X}")
            rec.setdefault("field_header_offset", field_offset)
        r.align(4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    data = args.input.read_bytes()
    r = Reader(data)
    records: list[dict] = []
    top_index = 0
    errors = []
    while r.pos < len(data) - 7:
        start = r.pos
        try:
            top_hash = r.u32()
            path = f"top[{top_index}]:{top_hash:08X}"
            parse_class(r, path, records)
            top_index += 1
        except Exception as exc:
            errors.append({"offset": r.pos, "start": start, "error": str(exc)})
            break
    args.output.write_text(json.dumps({
        "input": str(args.input),
        "length": len(data),
        "parsed_to": r.pos,
        "top_level_count": top_index,
        "errors": errors,
        "records": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"length": len(data), "parsed_to": r.pos, "top_level_count": top_index, "records": len(records), "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
