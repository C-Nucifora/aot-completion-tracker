# PC save research

Original Wings of Freedom, Steam 449800 build 1361480. Not AOT2. Build-specific offsets.

## Decryption

0xBBE20-byte file. Header little-endian u16 checksum and seed. For each u32 after offset 4, take three `state = (state * 0x5B1A7851 + 0xCE4E) & 0xffffffff` steps, XOR with state. Checksum: sum decrypted payload u16 words mod 65536. Both real slots pass. Derived read-only from load routine RVA 0x42D1A0. No re-encryption or save writing.

Serialization routines: RVAs 0x145900, 0x14A7E0, 0x13EBA0, 0x141490. Main state file 0x640 corresponds to runtime +8; first-block shift 0x638.

- Characters 0x249F0, 14 x 0xF0. +0x40 kills, +0x48 battles, +0x70 six u16 attributes, +0x80 XP, +0x84 zero-based level, +0xD4 additional XP, +0xD8 additional level. Character kills sum to global count at file 0x64C.
- Inventory 0x257C0: three groups of 100 x 0x40, group stride 0x1900. Byte 0 ID, 0xff empty, byte 1 fortification. Star data retained raw until mapped.
- Materials 0x362C0, 128 x 0x30. u32 count, +4 shop state. Names in English localization order.
- Requests 0x40AC8, 81 pairs normal/TAM, value 3 complete. Other states retained raw.
- Missions 0xA70, 600 x 0x60 per mode, TAM +0xE880. Flag 0x20 completed (RVA 0x112230 confirms); +8 time seconds. Rank and other fields raw.
- Gallery acquired if flags & 3. Equipment 0x24328/0x24428/0x24528, horses 0x24628, public information 0x1E008, Muster Roll 0x1E088, music 0x1DF00, Titans 0x24728. Separate from current inventory. Eligibility from parameter tables per RVA 0x14B220.

## Installed catalogue

English strings LINKDATA_EU_A entries 2869–2874. 2870 character/mission names, 2871 requests, 2872 equipment/materials, 2873 gallery. Archive directory: 16-byte header, <QII> entries with sector offsets x2048. Compressed data uses length-prefixed zlib chunks. Reference: https://github.com/TraduSquare/TitanUnpacker . No textures, audio, executable bytes or description prose distributed.

Runtime parameter pointer RVA 0xC14650. Equipment +8, 3 x128 x68: +4 development price, +12 upgrade price, +0x14 three stats, +0x20 parent, +0x22 four upgrade pairs, +0x32 four development pairs. Eligibility bytes +0x1B/+0x42 zero. Material prices at +0x69A4, stride16. Mission reward table +0x76E4, stride74: pairs0–2 normal clear,3–5 alternate normal clear,6–8 TAM clear,9–11 S-rank groups,12–14 Dire groups. Raw groups preserved. Known Perfected/Rozen recipes and Soldier's Dance rewards cross-check.

Unresolved: star fortification, rank enums, some gallery subrecord mappings. Unknown fields remain in raw exports. Random body-part drops require observed runs; they are not clear rewards.
