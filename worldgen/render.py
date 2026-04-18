from __future__ import annotations

import base64
import binascii
from collections import Counter
import errno
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Final

from .bedrock_chunks import (
    BlockInfo,
    ChunkDecodeError,
    DecodedSubchunk,
    OVERWORLD_DIMENSION_ID,
    SubchunkRecord,
    decode_subchunk,
    iter_packet_subchunk_records,
    iter_subchunk_records,
)
from .cache import utc_now_iso
from .config import WorldgenConfig
from .unknown_diagnostics import UnknownBlockDiagnostics


RENDER_BACKGROUND_COLOR: Final[tuple[int, int, int]] = (12, 16, 20)
MAX_METADATA_BLOCK_COUNTS: Final[int] = 60
HEADLESS_CHUNK_PACKET_FILE_NAME: Final[str] = 'headless_chunk_packets.jsonl'
CHUNK_TOUCH_MARKER_Y: Final[int] = -64
UNFINISHED_POINTS_COMPLETION_THRESHOLD: Final[float] = 90.0
CHUNK_TOUCH_MARKER_BLOCKS: Final[frozenset[str]] = frozenset((
    'bedrock',
    'minecraft:bedrock',
))


# UI-normalized colors sourced from the Blockbase Minecraft Block Color Code Generator
# chart, supplemented with renderer-specific aliases and diagnostics-derived runtime
# ID overrides for this Bedrock world.
BLOCK_COLOR_MAP: Final[dict[str, tuple[int, int, int] | None]] = {
    'acacia_wood': (199, 127, 74),
    'air': None,
    'amethyst_block': (153, 102, 204),
    'andesite': (167, 167, 167),
    'bamboo_mosaic': (124, 252, 0),
    'basalt': (75, 78, 87),
    'beacon': (0, 183, 235),
    'bedrock': (67, 67, 67),
    'birch_planks': (245, 222, 179),
    'black_wool': (29, 29, 29),
    'blackstone': (43, 46, 49),
    'blue_ice': (173, 216, 230),
    'blue_wool': (25, 25, 112),
    'bone_block': (255, 255, 224),
    'brick_block': (205, 92, 92),
    'brown_wool': (160, 82, 45),
    'carved_pumpkin': (255, 165, 0),
    'cave_air': None,
    'cherry_leaves': (255, 182, 193),
    'cherry_planks': (255, 192, 203),
    'copper_block': (184, 115, 51),
    'cyan_wool': (0, 206, 209),
    'dark_oak': (46, 27, 15),
    'dark_prismarine': (46, 107, 98),
    'deepslate': (74, 79, 82),
    'diamond_block': (93, 217, 217),
    'diorite': (225, 225, 225),
    'emerald_block': (34, 181, 115),
    'end_stone': (255, 250, 205),
    'glowstone': (251, 245, 208),
    'gold_block': (242, 193, 77),
    'granite': (194, 126, 106),
    'grass_block': (78, 139, 61),
    'gray_wool': (112, 128, 144),
    'hay_block': (238, 232, 170),
    'ice': (174, 227, 245),
    'iron_bars': (192, 192, 192),
    'iron_block': (200, 200, 200),
    'jungle_wood': (138, 75, 40),
    'kelp': (48, 112, 186),
    'lapis_block': (29, 59, 139),
    'lava': (229, 94, 26),
    'leaves': (34, 139, 34),
    'light_blue_concrete': (135, 206, 250),
    'lime_concrete': (144, 238, 144),
    'lime_shulker_box': (154, 205, 50),
    'magenta_wool': (218, 112, 214),
    'magma': (229, 94, 26),
    'mangrove_planks': (210, 105, 30),
    'melon': (152, 251, 152),
    'melon_block': (152, 251, 152),
    'moss_block': (85, 107, 47),
    'mud': (143, 151, 121),
    'nether_brick': (139, 0, 0),
    'netherite_block': (60, 60, 60),
    'netherrack': (178, 34, 34),
    'oak_planks': (181, 140, 82),
    'obsidian': (26, 15, 43),
    'orange_wool': (255, 69, 0),
    'packed_ice': (176, 224, 230),
    'pink_concrete': (255, 209, 220),
    'pink_wool': (242, 139, 178),
    'podzol': (123, 63, 0),
    'polished_deepslate': (112, 128, 144),
    'polished_granite': (188, 143, 143),
    'prismarine': (93, 175, 157),
    'purple_concrete': (128, 0, 128),
    'quartz_block': (237, 230, 223),
    'red_sand': (201, 110, 61),
    'redstone_block': (208, 0, 0),
    'sand': (227, 217, 166),
    'sandstone': (255, 232, 194),
    'scaffolding': (189, 183, 107),
    'sea_lantern': (221, 246, 244),
    'sea_pickle': (127, 255, 212),
    'seagrass': (48, 112, 186),
    'slime_block': (0, 255, 127),
    'snow': (238, 244, 247),
    'spruce_planks': (139, 69, 19),
    'stone': (125, 125, 125),
    'stone_bricks': (158, 158, 158),
    'terracotta': (255, 218, 185),
    'tuff': (122, 122, 118),
    'void_air': None,
    'water': (48, 112, 186),
    'white_wool': (245, 245, 220),
    'yellow_wool': (255, 215, 0),
}

BLOCK_COLOR_ALIASES: Final[dict[str, str]] = {
    'acacia_leaves': 'leaves',
    'acacia_log': 'acacia_wood',
    'acacia_planks': 'acacia_wood',
    'acacia_wood': 'acacia_wood',
    'azalea_leaves': 'leaves',
    'birch_leaves': 'leaves',
    'birch_log': 'birch_planks',
    'birch_wood': 'birch_planks',
    'block_of_quartz': 'quartz_block',
    'bubble_column': 'water',
    'calcite': 'quartz_block',
    'cherry_log': 'cherry_planks',
    'cherry_wood': 'cherry_planks',
    'chiseled_tuff_bricks': 'stone_bricks',
    'clay': 'terracotta',
    'coal_ore': 'stone',
    'cobblestone': 'stone',
    'copper_ore': 'stone',
    'dark_oak_leaves': 'leaves',
    'dark_oak_log': 'dark_oak',
    'dark_oak_planks': 'dark_oak',
    'dark_oak_wood': 'dark_oak',
    'deepslate_coal_ore': 'deepslate',
    'deepslate_copper_ore': 'deepslate',
    'deepslate_diamond_ore': 'deepslate',
    'deepslate_emerald_ore': 'deepslate',
    'deepslate_gold_ore': 'deepslate',
    'deepslate_iron_ore': 'deepslate',
    'deepslate_lapis_ore': 'deepslate',
    'deepslate_redstone_ore': 'deepslate',
    'diamond_ore': 'stone',
    'dirt_path': 'podzol',
    'emerald_ore': 'stone',
    'fern': 'grass_block',
    'flowering_azalea_leaves': 'leaves',
    'gold_ore': 'stone',
    'grass_path': 'podzol',
    'iron_ore': 'stone',
    'jungle_leaves': 'leaves',
    'jungle_log': 'jungle_wood',
    'jungle_planks': 'jungle_wood',
    'jungle_wood': 'jungle_wood',
    'kelp': 'kelp',
    'lapis_ore': 'stone',
    'lava': 'lava',
    'magma': 'magma',
    'mangrove_log': 'mangrove_planks',
    'mangrove_wood': 'mangrove_planks',
    'moss_carpet': 'moss_block',
    'mossy_cobblestone': 'moss_block',
    'mycelium': 'podzol',
    'oak_fence': 'oak_planks',
    'oak_leaves': 'leaves',
    'oak_log': 'oak_wood',
    'oak_planks': 'oak_planks',
    'oak_wood': 'oak_planks',
    'polished_tuff': 'tuff',
    'redstone_ore': 'stone',
    'seagrass': 'seagrass',
    'short_grass': 'grass_block',
    'smooth_basalt': 'basalt',
    'snow_block': 'snow',
    'snow_layer': 'snow',
    'spruce_leaves': 'leaves',
    'spruce_log': 'spruce_planks',
    'spruce_wood': 'spruce_planks',
    'tall_grass': 'grass_block',
    'tuff': 'tuff',
    'tuff_bricks': 'stone_bricks',
    'vine': 'leaves',
    'water': 'water',
    'waterlogged': 'water',
    'waxed_copper': 'copper_block',
    'waxed_copper_grate': 'copper_block',
    'waxed_oxidized_copper': 'copper_block',
    'waxed_oxidized_cut_copper': 'copper_block',
}

UNKNOWN_RUNTIME_ID_BLOCK_OVERRIDES: Final[dict[int, str]] = {
    -2147346391: 'minecraft:vault',
    -2144275372: 'minecraft:vault',
    -2144239176: 'minecraft:white_concrete',
    -2140481732: 'minecraft:raw_iron_block',
    -2137139075: 'minecraft:big_dripleaf',
    -2133956881: 'minecraft:candle',
    -2117142984: 'minecraft:water',
    -2098466397: 'minecraft:polished_tuff_slab',
    -2094354234: 'minecraft:vine',
    -2092079255: 'minecraft:carrots',
    -2081931148: 'minecraft:pink_petals',
    -2075594678: 'minecraft:cave_vines',
    -2063928837: 'minecraft:oak_stairs',
    -2063894143: 'minecraft:allium',
    -2040177125: 'minecraft:fence_gate',
    -2030732829: 'minecraft:chest',
    -2023452086: 'minecraft:calcite',
    -2022784304: 'minecraft:moss_carpet',
    -2005854751: 'minecraft:oxidized_cut_copper',
    -2002130453: 'minecraft:fern',
    -2001507684: 'minecraft:flower_pot',
    -1994193338: 'minecraft:water',
    -1980271023: 'minecraft:yellow_stained_glass_pane',
    -1979045823: 'minecraft:waxed_oxidized_chiseled_copper',
    -1973680577: 'minecraft:lava',
    -1945474061: 'minecraft:tall_grass',
    -1940979191: 'minecraft:oak_stairs',
    -1894786788: 'minecraft:big_dripleaf',
    -1888063654: 'minecraft:peony',
    -1871243692: 'minecraft:water',
    -1863621410: 'minecraft:cocoa',
    -1844802290: 'minecraft:waxed_copper_bulb',
    -1829237238: 'minecraft:ladder',
    -1825953308: 'minecraft:mud',
    -1823684660: 'minecraft:waxed_oxidized_copper_grate',
    -1810018825: 'minecraft:bed',
    -1798540142: 'minecraft:large_amethyst_bud',
    -1778856067: 'minecraft:hopper',
    -1770874571: 'minecraft:small_amethyst_bud',
    -1727781285: 'minecraft:lava',
    -1716206196: 'minecraft:dripstone_block',
    -1713001904: 'minecraft:big_dripleaf',
    -1706287592: 'minecraft:ladder',
    -1686701407: 'minecraft:rail',
    -1682960203: 'minecraft:infested_stone',
    -1672181533: 'minecraft:pumpkin',
    -1662802301: 'minecraft:trapdoor',
    -1660456241: 'minecraft:waxed_oxidized_copper',
    -1646145675: 'minecraft:pumpkin',
    -1627577175: 'minecraft:bush',
    -1625344400: 'minecraft:water',
    -1617722118: 'minecraft:cocoa',
    -1604831639: 'minecraft:lava',
    -1585068737: 'minecraft:pointed_dripstone',
    -1584874513: 'minecraft:pink_petals',
    -1583337946: 'minecraft:ladder',
    -1565556113: 'minecraft:lapis_ore',
    -1563751761: 'minecraft:rail',
    -1534107461: 'minecraft:white_tulip',
    -1502394754: 'minecraft:water',
    -1494772472: 'minecraft:cocoa',
    -1487217985: 'minecraft:waxed_cut_copper_stairs',
    -1485557914: 'minecraft:spruce_leaves',
    -1481881993: 'minecraft:lava',
    -1479606004: 'minecraft:vine',
    -1467211143: 'minecraft:leaf_litter',
    -1463053640: 'minecraft:pink_petals',
    -1455185414: 'minecraft:diamond_ore',
    -1447355868: 'minecraft:birch_log',
    -1445815089: 'minecraft:bamboo',
    -1440802115: 'minecraft:rail',
    -1436538438: 'minecraft:chest',
    -1435399120: 'minecraft:beetroot',
    -1411485687: 'minecraft:leaf_litter',
    -1408628467: 'minecraft:pink_petals',
    -1390153970: 'minecraft:potatoes',
    -1388783336: 'minecraft:waxed_oxidized_cut_copper_slab',
    -1364268339: 'minecraft:waxed_cut_copper_stairs',
    -1361711964: 'minecraft:leaf_litter',
    -1360840267: 'minecraft:short_grass',
    -1356656358: 'minecraft:vine',
    -1338000475: 'minecraft:copper_ore',
    -1318934348: 'minecraft:leaf_litter',
    -1305310020: 'minecraft:small_dripleaf_block',
    -1268732789: 'minecraft:obsidian',
    -1256495462: 'minecraft:water',
    -1241318693: 'minecraft:waxed_cut_copper_stairs',
    -1236877772: 'minecraft:gravel',
    -1235982701: 'minecraft:lava',
    -1214394359: 'minecraft:sandstone',
    -1212537786: 'minecraft:leaf_litter',
    -1199373513: 'minecraft:oak_slab',
    -1197720996: 'minecraft:brown_mushroom',
    -1195163360: 'minecraft:yellow_wool',
    -1173618887: 'minecraft:stone_stairs',
    -1162242455: 'minecraft:chiseled_tuff',
    -1133545816: 'minecraft:water',
    -1118369047: 'minecraft:waxed_cut_copper_stairs',
    -1116911787: 'minecraft:leaf_litter',
    -1113033055: 'minecraft:lava',
    -1093349422: 'minecraft:waxed_cut_copper_slab',
    -1066296665: 'minecraft:red_concrete',
    -1056550660: 'minecraft:waxed_copper_grate',
    -1041392617: 'minecraft:mangrove_leaves',
    -1040650625: 'minecraft:azure_bluet',
    -1032973274: 'minecraft:fence_gate',
    -1010596170: 'minecraft:water',
    -975514406: 'minecraft:pointed_dripstone',
    -966314981: 'minecraft:red_candle',
    -950948878: 'minecraft:waxed_oxidized_copper_door',
    -928902112: 'minecraft:andesite',
    -887646524: 'minecraft:water',
    -882949514: 'minecraft:wooden_door',
    -874952807: 'minecraft:mob_spawner',
    -873538651: 'minecraft:small_amethyst_bud',
    -872831514: 'minecraft:podzol',
    -867691717: 'minecraft:amethyst_cluster',
    -857810258: 'minecraft:oak_stairs',
    -855512174: 'minecraft:magma',
    -826053885: 'minecraft:rail',
    -813966384: 'minecraft:birch_leaves',
    -811410340: 'minecraft:cobblestone',
    -810765082: 'minecraft:brewing_stand',
    -805875711: 'minecraft:waxed_oxidized_copper_bulb',
    -805303123: 'minecraft:small_dripleaf_block',
    -781987925: 'minecraft:diorite',
    -744184117: 'minecraft:lava',
    -741908128: 'minecraft:vine',
    -734860612: 'minecraft:oak_stairs',
    -719121627: 'minecraft:red_candle',
    -712930245: 'minecraft:pink_tulip',
    -697412304: 'minecraft:stripped_oak_log',
    -689520712: 'minecraft:polished_tuff',
    -641747232: 'minecraft:water',
    -627848708: 'minecraft:leaf_litter',
    -611910966: 'minecraft:oak_stairs',
    -598113140: 'minecraft:glass_pane',
    -575868783: 'minecraft:pink_petals',
    -573079956: 'minecraft:infested_deepslate',
    -556655901: 'minecraft:white_wool',
    -552380121: 'minecraft:pumpkin',
    -548881537: 'minecraft:fence_gate',
    -532520228: 'minecraft:oak_log',
    -528392077: 'minecraft:rose_bush',
    -524945763: 'minecraft:fence_gate',
    -504047368: 'minecraft:cherry_leaves',
    -498284825: 'minecraft:lava',
    -488961320: 'minecraft:oak_stairs',
    -474042178: 'minecraft:big_dripleaf',
    -471320113: 'minecraft:dandelion',
    -451529364: 'minecraft:oak_planks',
    -442854870: 'minecraft:bed',
    -427830319: 'minecraft:bookshelf',
    -410119178: 'minecraft:grass_path',
    -336395115: 'minecraft:medium_amethyst_bud',
    -326305501: 'minecraft:mangrove_log',
    -323382185: 'minecraft:bell',
    -310094935: 'minecraft:red_mushroom',
    -299655562: 'minecraft:oak_fence',
    -292310610: 'minecraft:chest',
    -285775482: 'minecraft:oxeye_daisy',
    -285056957: 'minecraft:small_amethyst_bud',
    -283057762: 'minecraft:bed',
    -278420735: 'minecraft:medium_amethyst_bud',
    -241493329: 'minecraft:bed',
    -229722692: 'minecraft:iron_ore',
    -204266477: 'minecraft:waxed_copper_bulb',
    -199097559: 'minecraft:cherry_log',
    -144174066: 'minecraft:waxed_chiseled_copper',
    -142062413: 'minecraft:vault',
    -125505501: 'minecraft:dispenser',
    -110542841: 'minecraft:leaf_litter',
    -101418334: 'minecraft:lily_of_the_valley',
    -96897442: 'minecraft:waxed_cut_copper',
    -77455117: 'minecraft:dirt',
    -73538566: 'minecraft:oak_leaves',
    -65469750: 'minecraft:jungle_log',
    -64412287: 'minecraft:deepslate_copper_ore',
    -21030149: 'minecraft:bed',
    -6801812: 'minecraft:gold_ore',
    -6429763: 'minecraft:stone',
    6278990: 'minecraft:cave_vines',
    8271262: 'minecraft:jungle_log',
    21673810: 'minecraft:leaf_litter',
    31262384: 'minecraft:small_dripleaf_block',
    37401276: 'minecraft:pink_petals',
    46254943: 'minecraft:kelp',
    72581758: 'minecraft:waxed_oxidized_cut_copper',
    73409775: 'minecraft:waxed_copper',
    76694702: 'minecraft:kelp',
    100196662: 'minecraft:chiseled_tuff_bricks',
    125356546: 'minecraft:cherry_log',
    129228636: 'minecraft:cave_vines',
    145945547: 'minecraft:leaf_litter',
    169204589: 'minecraft:kelp',
    180927568: 'minecraft:leaf_litter',
    199644348: 'minecraft:kelp',
    215095754: 'minecraft:ice',
    231988512: 'minecraft:small_amethyst_bud',
    236001127: 'minecraft:medium_amethyst_bud',
    238880093: 'minecraft:tall_grass',
    239986577: 'minecraft:cobbled_deepslate',
    258356889: 'minecraft:big_dripleaf',
    277279430: 'minecraft:sand',
    292154235: 'minecraft:kelp',
    296290500: 'minecraft:peony',
    311381174: 'minecraft:decorated_pot',
    312851043: 'minecraft:wooden_door',
    319021775: 'minecraft:cocoa',
    322593994: 'minecraft:kelp',
    330287481: 'minecraft:cobblestone_slab',
    341144378: 'minecraft:emerald_ore',
    346490377: 'minecraft:bedrock',
    347114514: 'minecraft:pink_petals',
    357898165: 'minecraft:big_dripleaf',
    360427840: 'minecraft:redstone_ore',
    375127928: 'minecraft:cave_vines',
    376985472: 'minecraft:reeds',
    380909311: 'minecraft:jungle_leaves',
    384685437: 'minecraft:vault',
    388439619: 'minecraft:small_amethyst_bud',
    388857631: 'minecraft:tuff',
    389092996: 'minecraft:candle',
    393260102: 'minecraft:powder_snow',
    400339240: 'minecraft:polished_andesite',
    408309789: 'minecraft:torch',
    415103881: 'minecraft:kelp',
    431910331: 'minecraft:cave_vines_head_with_berries',
    434330820: 'minecraft:decorated_pot',
    445543640: 'minecraft:kelp',
    458779215: 'minecraft:oak_log',
    498077574: 'minecraft:cave_vines',
    507665031: 'minecraft:pink_petals',
    538053527: 'minecraft:kelp',
    549647086: 'minecraft:seagrass',
    554859977: 'minecraft:cave_vines_head_with_berries',
    555150098: 'minecraft:bee_nest',
    557280466: 'minecraft:decorated_pot',
    558773164: 'minecraft:bone_block',
    564921067: 'minecraft:cocoa',
    568493286: 'minecraft:kelp',
    574303055: 'minecraft:big_dripleaf',
    579193703: 'minecraft:stone_stairs',
    592690570: 'minecraft:vault',
    598477500: 'minecraft:deepslate_redstone_ore',
    599285417: 'minecraft:pointed_dripstone',
    619812562: 'minecraft:waxed_oxidized_copper_door',
    621027220: 'minecraft:cave_vines',
    626915046: 'minecraft:bed',
    658968714: 'minecraft:firefly_bush',
    661003173: 'minecraft:kelp',
    680230112: 'minecraft:decorated_pot',
    683310715: 'minecraft:sunflower',
    687870713: 'minecraft:cocoa',
    691442932: 'minecraft:kelp',
    693952458: 'minecraft:lilac',
    695824455: 'minecraft:leaf_litter',
    702143349: 'minecraft:stone_stairs',
    706713370: 'minecraft:wooden_button',
    712709230: 'minecraft:flowering_azalea',
    720905960: 'minecraft:deepslate_gold_ore',
    720984766: 'minecraft:farmland',
    728848923: 'minecraft:large_amethyst_bud',
    737468360: 'minecraft:smooth_basalt',
    743976866: 'minecraft:cave_vines',
    775906135: 'minecraft:glow_lichen',
    783952819: 'minecraft:kelp',
    813162157: 'minecraft:large_amethyst_bud',
    814392578: 'minecraft:kelp',
    825092995: 'minecraft:stone_stairs',
    858022194: 'minecraft:dispenser',
    858219760: 'minecraft:amethyst_cluster',
    866926512: 'minecraft:cave_vines',
    880102039: 'minecraft:bamboo',
    890633686: 'minecraft:packed_ice',
    901567082: 'minecraft:pink_petals',
    906902465: 'minecraft:kelp',
    919059136: 'minecraft:air',
    929395227: 'minecraft:iron_chain',
    937342224: 'minecraft:kelp',
    948042641: 'minecraft:stone_stairs',
    960319816: 'minecraft:mangrove_wood',
    960862733: 'minecraft:cocoa',
    988439562: 'minecraft:bamboo',
    1002086352: 'minecraft:barrel',
    1006639912: 'minecraft:mangrove_roots',
    1014900938: 'minecraft:spruce_log',
    1029852111: 'minecraft:kelp',
    1037715164: 'minecraft:seagrass',
    1073379657: 'minecraft:pink_petals',
    1075073506: 'minecraft:leaf_litter',
    1079334427: 'minecraft:big_dripleaf',
    1083795723: 'minecraft:pink_petals',
    1083812379: 'minecraft:cocoa',
    1086553075: 'minecraft:red_tulip',
    1102296081: 'minecraft:moss_block',
    1107104048: 'minecraft:medium_amethyst_bud',
    1109202945: 'minecraft:medium_amethyst_bud',
    1134407319: 'minecraft:grass_block',
    1152801757: 'minecraft:kelp',
    1153302030: 'minecraft:small_amethyst_bud',
    1154764142: 'minecraft:stone_button',
    1158016212: 'minecraft:muddy_mangrove_roots',
    1169608207: 'minecraft:cave_vines_head_with_berries',
    1170341981: 'minecraft:waxed_oxidized_cut_copper_slab',
    1186780911: 'minecraft:copper_block',
    1190700923: 'minecraft:snow_layer',
    1202819533: 'minecraft:leaf_litter',
    1206762025: 'minecraft:cocoa',
    1208839748: 'minecraft:pointed_dripstone',
    1209499071: 'minecraft:air',
    1235096474: 'minecraft:red_glazed_terracotta',
    1235586297: 'minecraft:trapdoor',
    1235775450: 'minecraft:cave_vines',
    1241777929: 'minecraft:dispenser',
    1257643209: 'minecraft:large_amethyst_bud',
    1275751403: 'minecraft:kelp',
    1281466637: 'minecraft:wooden_door',
    1290277767: 'minecraft:leaf_litter',
    1292557853: 'minecraft:cave_vines_head_with_berries',
    1297775349: 'minecraft:mangrove_wood',
    1301404640: 'minecraft:wooden_door',
    1307197784: 'minecraft:waxed_oxidized_copper_door',
    1333748428: 'minecraft:clay',
    1358046120: 'minecraft:red_glazed_terracotta',
    1358725096: 'minecraft:cave_vines',
    1360438910: 'minecraft:deepslate_coal_ore',
    1370767346: 'minecraft:coal_ore',
    1375022725: 'minecraft:bell',
    1383693832: 'minecraft:vault',
    1398701049: 'minecraft:kelp',
    1398910214: 'minecraft:pink_petals',
    1416660683: 'minecraft:lilac',
    1427302426: 'minecraft:sunflower',
    1443775054: 'minecraft:pumpkin',
    1462915105: 'minecraft:azalea',
    1470550531: 'minecraft:mossy_cobblestone',
    1472927537: 'minecraft:white_stained_glass',
    1476464219: 'minecraft:large_amethyst_bud',
    1482638520: 'minecraft:cave_vines_body_with_berries',
    1483765952: 'minecraft:chest',
    1499653246: 'minecraft:vault',
    1521650695: 'minecraft:kelp',
    1522918703: 'minecraft:waxed_oxidized_cut_copper_stairs',
    1538457145: 'minecraft:cave_vines_head_with_berries',
    1540099352: 'minecraft:oxidized_copper_trapdoor',
    1545251188: 'minecraft:waxed_exposed_copper_bulb',
    1574180580: 'minecraft:composter',
    1574827030: 'minecraft:waxed_weathered_copper_bulb',
    1581632288: 'minecraft:farmland',
    1603945412: 'minecraft:red_glazed_terracotta',
    1622144230: 'minecraft:deepslate_diamond_ore',
    1635287720: 'minecraft:waxed_cut_copper_slab',
    1636753508: 'minecraft:pink_petals',
    1644600341: 'minecraft:kelp',
    1645868349: 'minecraft:waxed_oxidized_cut_copper_stairs',
    1651833926: 'minecraft:oak_log',
    1655962077: 'minecraft:rose_bush',
    1656561015: 'minecraft:seagrass',
    1661406791: 'minecraft:cave_vines_head_with_berries',
    1663895583: 'minecraft:amethyst_block',
    1675040100: 'minecraft:kelp',
    1678361926: 'minecraft:amethyst_cluster',
    1729794013: 'minecraft:amethyst_cluster',
    1753984027: 'minecraft:poppy',
    1767549987: 'minecraft:kelp',
    1768817995: 'minecraft:waxed_oxidized_cut_copper_stairs',
    1781156841: 'minecraft:melon_block',
    1784356437: 'minecraft:cave_vines_head_with_berries',
    1808975374: 'minecraft:water',
    1819383315: 'minecraft:granite',
    1844991522: 'minecraft:white_stained_glass_pane',
    1850195819: 'minecraft:deepslate_lapis_ore',
    1881126159: 'minecraft:lectern',
    1890499633: 'minecraft:kelp',
    1891767641: 'minecraft:waxed_oxidized_cut_copper_stairs',
    1892462018: 'minecraft:stone_button',
    1907306083: 'minecraft:cave_vines_head_with_berries',
    1913784134: 'minecraft:pink_petals',
    1916213589: 'minecraft:waxed_oxidized_copper_door',
    1920567035: 'minecraft:amethyst_cluster',
    1929237587: 'minecraft:trial_spawner',
    1931925020: 'minecraft:water',
    1943056583: 'minecraft:pink_petals',
    1985139167: 'minecraft:oak_stairs',
    1985256595: 'minecraft:cherry_log',
    1988415940: 'minecraft:deepslate',
    2015411664: 'minecraft:stone_button',
    2022951443: 'minecraft:orange_tulip',
    2030255729: 'minecraft:cave_vines_head_with_berries',
    2052187233: 'minecraft:trial_spawner',
    2054874666: 'minecraft:water',
    2073048256: 'minecraft:dispenser',
    2077663416: 'minecraft:vine',
    2093415505: 'minecraft:leaf_litter',
    2094950560: 'minecraft:deepslate_iron_ore',
    2096098347: 'minecraft:tuff_bricks',
    2102780256: 'minecraft:trapdoor',
    2102997316: 'minecraft:white_terracotta',
    2108088813: 'minecraft:oak_stairs',
    2118884404: 'minecraft:jungle_log',
    2122928911: 'minecraft:cornflower',
    2125544031: 'minecraft:budding_amethyst',
    2127919466: 'minecraft:raw_copper_block',
    2129958493: 'minecraft:pink_petals',
    2141875526: 'minecraft:small_dripleaf_block',
}


@dataclass(frozen=True, slots=True)
class RenderPlan:
    generated_at: str
    center_label: str
    center_x: int
    center_z: int
    radius: int
    sample_step: int
    min_x: int
    max_x: int
    min_z: int
    max_z: int
    world_path: str | None
    note: str


@dataclass(frozen=True, slots=True)
class TopBlock:
    y: int
    block_name: str


@dataclass(frozen=True, slots=True)
class UncoloredBlockSample:
    world_x: int
    world_y: int
    world_z: int
    chunk_x: int
    chunk_z: int
    subchunk_y: int
    local_x: int
    local_y: int
    local_z: int
    source: str
    storage_index: int
    palette_index: int
    runtime_id: int | None
    bits_per_block: int
    palette_size: int


@dataclass(slots=True)
class UncoloredBlockStats:
    block_name: str
    count: int = 0
    min_y: int | None = None
    max_y: int | None = None
    sources: Counter[str] = field(default_factory=Counter)
    runtime_ids: set[int] = field(default_factory=set)
    storage_indices: set[int] = field(default_factory=set)
    bits_per_block_values: set[int] = field(default_factory=set)
    palette_sizes: set[int] = field(default_factory=set)
    chunks: set[tuple[int, int]] = field(default_factory=set)
    samples: list[UncoloredBlockSample] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RenderResult:
    generated_at: str
    image_path: str
    metadata_path: str
    world_path: str
    width: int
    height: int
    min_x: int
    max_x: int
    min_z: int
    max_z: int
    sample_step: int
    chunk_columns_requested: int
    chunk_columns_read: int
    chunk_columns_missing: int
    subchunks_read: int
    subchunks_skipped_below_surface: int
    subchunk_decode_errors: int
    total_pixels: int
    colored_pixels: int
    colored_min_x: int | None
    colored_max_x: int | None
    colored_min_z: int | None
    colored_max_z: int | None
    map_completion_percent: float
    unfinished_points_path: str
    unfinished_point_count: int
    unfinished_group_count: int
    block_counts: dict[str, int]
    uncolored_blocks_report_path: str
    uncolored_block_occurrences: int
    uncolored_block_counts: dict[str, int]
    unknown_block_diagnostics_path: str | None = None
    unknown_block_occurrences_csv_path: str | None = None
    unknown_block_summary_path: str | None = None
    unknown_block_persistent_candidates_path: str | None = None
    render_style: str = 'surface'
    fixed_y: int | None = None


def build_render_plan(config: WorldgenConfig, world_path: Path | None = None) -> RenderPlan:
    render = config.render
    return RenderPlan(
        generated_at=utc_now_iso(),
        center_label=render.center_label,
        center_x=render.center_x,
        center_z=render.center_z,
        radius=render.radius,
        sample_step=render.sample_step,
        min_x=render.min_x,
        max_x=render.max_x,
        min_z=render.min_z,
        max_z=render.max_z,
        world_path=str(world_path.resolve()) if world_path else None,
        note=(
            'Top-down render plan. The first renderer reads generated Bedrock chunks only; '
            'it does not pre-generate missing terrain.'
        ),
    )


def save_render_plan(path: Path, plan: RenderPlan) -> None:
    _write_text_atomically_with_retry(
        path,
        json.dumps(asdict(plan), indent=2, sort_keys=True) + '\n',
    )


def render_topdown_map(
    config: WorldgenConfig,
    world_path: Path | None,
    *,
    image_path: Path,
    metadata_path: Path,
    diagnose_unknown_blocks: bool = False,
    prefer_persistent_bedrock: bool = False,
    packet_cache_path: Path | None = None,
    packet_cache_paths: tuple[Path, ...] | None = None,
    read_persistent_bedrock: bool = True,
    read_packet_cache: bool = True,
    preserve_existing_image: bool = False,
    fixed_y: int | None = None,
    pixel_keys: set[tuple[int, int]] | None = None,
    compact_packet_cache: bool = True,
    image_progress_callback: Callable[[int], None] | None = None,
    image_progress_interval: int = 0,
    image_progress_min_seconds: float = 0.75,
) -> RenderResult:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            'Rendering PNG output requires Pillow. Install it with `python3 -m pip install Pillow`.'
        ) from exc
    Image.MAX_IMAGE_PIXELS = None

    render = config.render
    generated_at = utc_now_iso()
    width = _sampled_axis_size(render.min_x, render.max_x, render.sample_step)
    height = _sampled_axis_size(render.min_z, render.max_z, render.sample_step)
    min_chunk_x = render.min_x // 16
    max_chunk_x = render.max_x // 16
    min_chunk_z = render.min_z // 16
    max_chunk_z = render.max_z // 16
    record_min_chunk_x = min_chunk_x
    record_max_chunk_x = max_chunk_x
    record_min_chunk_z = min_chunk_z
    record_max_chunk_z = max_chunk_z
    if pixel_keys is not None:
        if not pixel_keys:
            raise ValueError('pixel_keys must be None or a non-empty set.')
        target_chunk_x_values = {
            (render.min_x + (pixel_x * render.sample_step)) // 16
            for pixel_x, _pixel_z in pixel_keys
        }
        target_chunk_z_values = {
            (render.min_z + (pixel_z * render.sample_step)) // 16
            for _pixel_x, pixel_z in pixel_keys
        }
        record_min_chunk_x = max(min_chunk_x, min(target_chunk_x_values))
        record_max_chunk_x = min(max_chunk_x, max(target_chunk_x_values))
        record_min_chunk_z = max(min_chunk_z, min(target_chunk_z_values))
        record_max_chunk_z = min(max_chunk_z, max(target_chunk_z_values))
    chunk_columns_requested = (
        (max_chunk_x - min_chunk_x + 1)
        * (max_chunk_z - min_chunk_z + 1)
    )

    top_blocks: dict[tuple[int, int], TopBlock] = {}
    uncolored_blocks: dict[str, UncoloredBlockStats] = {}
    persistent_records = ()
    if read_persistent_bedrock and world_path is not None:
        persistent_records = tuple(
            iter_subchunk_records(
                world_path,
                min_chunk_x=record_min_chunk_x,
                max_chunk_x=record_max_chunk_x,
                min_chunk_z=record_min_chunk_z,
                max_chunk_z=record_max_chunk_z,
            )
        )
    packet_cache_paths = packet_cache_paths or (
        packet_cache_path or config.storage.cache_dir / HEADLESS_CHUNK_PACKET_FILE_NAME,
    )
    source_path = world_path or packet_cache_paths[-1]
    packet_records = ()
    if read_packet_cache:
        packet_record_by_key: dict[tuple[int | None, int, int, int, bool], SubchunkRecord] = {}
        for active_packet_cache_path in packet_cache_paths:
            active_packet_records = _iter_cached_packet_subchunk_records(
                active_packet_cache_path,
                min_chunk_x=record_min_chunk_x,
                max_chunk_x=record_max_chunk_x,
                min_chunk_z=record_min_chunk_z,
                max_chunk_z=record_max_chunk_z,
            )
            if compact_packet_cache and active_packet_cache_path == packet_cache_paths[-1]:
                _compact_cached_packet_subchunk_records(active_packet_cache_path, active_packet_records)
            for packet_record in active_packet_records:
                packet_record_by_key[
                    (
                        packet_record.dimension_id,
                        packet_record.chunk_x,
                        packet_record.chunk_z,
                        packet_record.subchunk_y,
                        packet_record.uses_runtime_palette,
                    )
                ] = packet_record
        packet_records = tuple(packet_record_by_key.values())
    packet_records = _filter_packet_records_against_persistent_columns(
        packet_records,
        persistent_records=persistent_records,
    )
    persistent_subchunks: dict[tuple[int | None, int, int, int], DecodedSubchunk] = {}
    decoded_subchunks: dict[tuple[str, int, int, int], DecodedSubchunk] = {}
    if diagnose_unknown_blocks and prefer_persistent_bedrock:
        for record in persistent_records:
            try:
                decoded_subchunk = decode_subchunk(record)
            except ChunkDecodeError:
                continue
            persistent_key = (
                record.dimension_id,
                record.chunk_x,
                record.chunk_z,
                decoded_subchunk.subchunk_y,
            )
            persistent_subchunks[persistent_key] = decoded_subchunk
            decoded_subchunks[_record_cache_key(record)] = decoded_subchunk

    unknown_diagnostics = None
    if diagnose_unknown_blocks:
        if world_path is None:
            raise RuntimeError('Unknown block diagnostics require a Bedrock world folder.')
        unknown_diagnostics = UnknownBlockDiagnostics(
            world_path=world_path,
            generated_at=generated_at,
            persistent_subchunks=persistent_subchunks if prefer_persistent_bedrock else None,
        )
    chunk_columns_read: set[tuple[int, int]] = set()
    subchunks_read = 0
    subchunks_skipped_below_surface = 0
    subchunk_decode_errors = 0

    records = sorted(
        (*persistent_records, *packet_records),
        key=lambda record: (
            record.subchunk_y,
            1 if not record.uses_runtime_palette else 0,
            record.chunk_z,
            record.chunk_x,
        ),
        reverse=True,
    )

    for record in records:
        chunk_columns_read.add((record.chunk_x, record.chunk_z))
        subchunk: DecodedSubchunk | None = None
        if fixed_y is None:
            could_improve_top_blocks = _subchunk_could_improve_top_blocks(
                top_blocks,
                record,
                min_x=render.min_x,
                max_x=render.max_x,
                min_z=render.min_z,
                max_z=render.max_z,
                sample_step=render.sample_step,
                pixel_keys=pixel_keys,
            )
        else:
            could_improve_top_blocks = record.subchunk_y == fixed_y // 16

        if unknown_diagnostics is not None:
            try:
                subchunk = decoded_subchunks.get(_record_cache_key(record)) or decode_subchunk(record)
            except ChunkDecodeError as exc:
                subchunk_decode_errors += 1
                unknown_diagnostics.record_decode_error(record, exc)
                continue
            subchunks_read += 1
            unknown_diagnostics.collect_subchunk(subchunk)

        if not could_improve_top_blocks:
            subchunks_skipped_below_surface += 1
            continue

        if subchunk is None:
            try:
                subchunk = decoded_subchunks.get(_record_cache_key(record)) or decode_subchunk(record)
            except ChunkDecodeError:
                subchunk_decode_errors += 1
                continue
            subchunks_read += 1
        if fixed_y is None:
            _collect_subchunk_top_blocks(
                top_blocks,
                subchunk,
                uncolored_blocks,
                min_x=render.min_x,
                max_x=render.max_x,
                min_z=render.min_z,
                max_z=render.max_z,
                sample_step=render.sample_step,
                pixel_keys=pixel_keys,
            )
        else:
            _collect_subchunk_fixed_y_blocks(
                top_blocks,
                subchunk,
                uncolored_blocks,
                fixed_y=fixed_y,
                min_x=render.min_x,
                max_x=render.max_x,
                min_z=render.min_z,
                max_z=render.max_z,
                sample_step=render.sample_step,
                pixel_keys=pixel_keys,
            )

    image = None
    if preserve_existing_image and image_path.exists():
        try:
            existing_image = Image.open(image_path).convert('RGBA')
            if existing_image.size == (width, height):
                image = existing_image
        except OSError:
            image = None
    if image is None:
        image = Image.new('RGBA', (width, height), (*RENDER_BACKGROUND_COLOR, 0))
    pixels = image.load()
    if pixels is None:
        raise RuntimeError('Could not access rendered map pixels.')
    newly_colored_pixels = 0
    next_progress_pixels = image_progress_interval
    last_progress_at = 0.0
    for (pixel_x, pixel_z), top_block in top_blocks.items():
        block_color = _block_color(top_block.block_name)
        if block_color is not None:
            previous_pixel = pixels[pixel_x, pixel_z]
            pixels[pixel_x, pixel_z] = (*block_color, 255)
            previous_alpha = (
                previous_pixel[3]
                if isinstance(previous_pixel, tuple) and len(previous_pixel) >= 4
                else 255
            )
            if previous_alpha == 0:
                newly_colored_pixels += 1
                if (
                    image_progress_callback is not None
                    and image_progress_interval > 0
                    and newly_colored_pixels >= next_progress_pixels
                ):
                    now = time.monotonic()
                    if last_progress_at == 0.0 or now - last_progress_at >= image_progress_min_seconds:
                        image_progress_callback(newly_colored_pixels)
                        last_progress_at = now
                    next_progress_pixels = newly_colored_pixels + image_progress_interval
    visible_pixel_count, colored_min_x, colored_max_x, colored_min_z, colored_max_z = (
        _visible_image_world_bounds(
            image,
            min_x=render.min_x,
            min_z=render.min_z,
            sample_step=render.sample_step,
        )
    )
    if visible_pixel_count == 0:
        _draw_no_chunks_message(image)
        visible_pixel_count, colored_min_x, colored_max_x, colored_min_z, colored_max_z = (
            _visible_image_world_bounds(
                image,
                min_x=render.min_x,
                min_z=render.min_z,
                sample_step=render.sample_step,
            )
        )

    _save_image_with_retry(image, image_path)
    if image_path.name == 'blackport_topdown.png':
        uncolored_blocks_report_path = image_path.with_name('uncolored_blocks_report.txt')
    else:
        uncolored_blocks_report_path = image_path.with_name(
            f'{image_path.stem}_uncolored_blocks_report.txt'
        )
    map_completion_percent = _map_completion_percent(visible_pixel_count, width * height)
    unfinished_points_path = _unfinished_points_report_path(image_path)
    unfinished_point_count, unfinished_group_count = _write_unfinished_points_report(
        unfinished_points_path,
        image,
        generated_at=generated_at,
        world_path=source_path,
        render_min_x=render.min_x,
        render_max_x=render.max_x,
        render_min_z=render.min_z,
        render_max_z=render.max_z,
        sample_step=render.sample_step,
        colored_pixels=visible_pixel_count,
        total_pixels=width * height,
        completion_percent=map_completion_percent,
        colored_min_x=colored_min_x,
        colored_max_x=colored_max_x,
        colored_min_z=colored_min_z,
        colored_max_z=colored_max_z,
    )
    _write_uncolored_blocks_report(
        uncolored_blocks_report_path,
        uncolored_blocks,
        generated_at=utc_now_iso(),
        world_path=source_path,
        render_min_x=render.min_x,
        render_max_x=render.max_x,
        render_min_z=render.min_z,
        render_max_z=render.max_z,
        sample_step=render.sample_step,
    )

    unknown_block_diagnostics_path: Path | None = None
    unknown_block_occurrences_csv_path: Path | None = None
    unknown_block_summary_path: Path | None = None
    unknown_block_persistent_candidates_path: Path | None = None
    if unknown_diagnostics is not None:
        unknown_block_diagnostics_path = image_path.with_name('unknown_block_diagnostics.json')
        unknown_block_occurrences_csv_path = image_path.with_name('unknown_block_occurrences.csv')
        unknown_block_summary_path = image_path.with_name('unknown_block_summary.txt')
        unknown_block_persistent_candidates_path = image_path.with_name(
            'unknown_block_persistent_candidates.json'
        )
        unknown_diagnostics.write_reports(
            json_path=unknown_block_diagnostics_path,
            csv_path=unknown_block_occurrences_csv_path,
            summary_path=unknown_block_summary_path,
            persistent_candidates_path=unknown_block_persistent_candidates_path,
        )

    block_counts = dict(
        Counter(block.block_name for block in top_blocks.values()).most_common(MAX_METADATA_BLOCK_COUNTS)
    )
    uncolored_block_counts = dict(
        Counter(
            {
                block_name: stats.count
                for block_name, stats in uncolored_blocks.items()
            }
        ).most_common(MAX_METADATA_BLOCK_COUNTS)
    )
    result = RenderResult(
        generated_at=generated_at,
        image_path=str(image_path.resolve()),
        metadata_path=str(metadata_path.resolve()),
        world_path=str(source_path.resolve()),
        width=width,
        height=height,
        min_x=render.min_x,
        max_x=render.max_x,
        min_z=render.min_z,
        max_z=render.max_z,
        sample_step=render.sample_step,
        chunk_columns_requested=chunk_columns_requested,
        chunk_columns_read=len(chunk_columns_read),
        chunk_columns_missing=max(0, chunk_columns_requested - len(chunk_columns_read)),
        subchunks_read=subchunks_read,
        subchunks_skipped_below_surface=subchunks_skipped_below_surface,
        subchunk_decode_errors=subchunk_decode_errors,
        total_pixels=width * height,
        colored_pixels=visible_pixel_count,
        colored_min_x=colored_min_x,
        colored_max_x=colored_max_x,
        colored_min_z=colored_min_z,
        colored_max_z=colored_max_z,
        map_completion_percent=map_completion_percent,
        unfinished_points_path=str(unfinished_points_path.resolve()),
        unfinished_point_count=unfinished_point_count,
        unfinished_group_count=unfinished_group_count,
        block_counts=block_counts,
        uncolored_blocks_report_path=str(uncolored_blocks_report_path.resolve()),
        uncolored_block_occurrences=sum(stats.count for stats in uncolored_blocks.values()),
        uncolored_block_counts=uncolored_block_counts,
        unknown_block_diagnostics_path=(
            str(unknown_block_diagnostics_path.resolve())
            if unknown_block_diagnostics_path is not None
            else None
        ),
        unknown_block_occurrences_csv_path=(
            str(unknown_block_occurrences_csv_path.resolve())
            if unknown_block_occurrences_csv_path is not None
            else None
        ),
        unknown_block_summary_path=(
            str(unknown_block_summary_path.resolve())
            if unknown_block_summary_path is not None
            else None
        ),
        unknown_block_persistent_candidates_path=(
            str(unknown_block_persistent_candidates_path.resolve())
            if unknown_block_persistent_candidates_path is not None
            else None
        ),
        render_style='fixed_y' if fixed_y is not None else 'surface',
        fixed_y=fixed_y,
    )
    save_render_result(metadata_path, result)
    return result


def _iter_cached_packet_subchunk_records(
    packet_cache_path: Path,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> tuple[SubchunkRecord, ...]:
    if not packet_cache_path.exists():
        return ()

    latest_records: dict[tuple[int, int, int, bool], SubchunkRecord] = {}
    try:
        lines = packet_cache_path.open(encoding='utf-8')
    except OSError:
        return ()

    with lines:
        for line in lines:
            if not line.strip():
                continue
            record = _cached_packet_record_from_line(
                line,
                min_chunk_x=min_chunk_x,
                max_chunk_x=max_chunk_x,
                min_chunk_z=min_chunk_z,
                max_chunk_z=max_chunk_z,
            )
            if record is not None:
                for subchunk_record in record:
                    latest_records[
                        (
                            subchunk_record.chunk_x,
                            subchunk_record.chunk_z,
                            subchunk_record.subchunk_y,
                            subchunk_record.uses_runtime_palette,
                        )
                    ] = subchunk_record
    return tuple(latest_records.values())


def _compact_cached_packet_subchunk_records(
    packet_cache_path: Path,
    records: tuple[SubchunkRecord, ...],
) -> None:
    if not records or not packet_cache_path.exists():
        return

    compacted_at = utc_now_iso()
    lines = []
    for record in records:
        if not record.payload:
            continue
        lines.append(
            json.dumps(
                {
                    'type': 'subchunk',
                    'generated_at': compacted_at,
                    'x': record.chunk_x,
                    'z': record.chunk_z,
                    'dimension': (
                        record.dimension_id
                        if record.dimension_id is not None
                        else OVERWORLD_DIMENSION_ID
                    ),
                    'subchunk_y': record.subchunk_y,
                    'payload_base64': base64.b64encode(record.payload).decode('ascii'),
                },
                sort_keys=True,
            )
        )

    if not lines:
        return

    temporary_path = packet_cache_path.with_suffix(f'{packet_cache_path.suffix}.tmp')
    try:
        temporary_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        temporary_path.replace(packet_cache_path)
    except OSError:
        try:
            temporary_path.unlink()
        except OSError:
            pass


def _record_cache_key(record: SubchunkRecord) -> tuple[str, int, int, int]:
    return (
        record.record_source,
        record.chunk_x,
        record.chunk_z,
        record.subchunk_y,
    )


def _record_column_key(record: SubchunkRecord) -> tuple[int, int, int]:
    return (
        OVERWORLD_DIMENSION_ID if record.dimension_id is None else record.dimension_id,
        record.chunk_x,
        record.chunk_z,
    )


def _filter_packet_records_against_persistent_columns(
    packet_records: tuple[SubchunkRecord, ...],
    *,
    persistent_records: tuple[SubchunkRecord, ...],
) -> tuple[SubchunkRecord, ...]:
    if not packet_records or not persistent_records:
        return packet_records

    persistent_columns = {_record_column_key(record) for record in persistent_records}
    return tuple(
        record
        for record in packet_records
        if _record_column_key(record) not in persistent_columns
    )


def _cached_packet_record_from_line(
    line: str,
    *,
    min_chunk_x: int,
    max_chunk_x: int,
    min_chunk_z: int,
    max_chunk_z: int,
) -> tuple[SubchunkRecord, ...] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    chunk_x = payload.get('x')
    chunk_z = payload.get('z')
    dimension = payload.get('dimension')
    sub_chunk_count = payload.get('sub_chunk_count')
    subchunk_y = payload.get('subchunk_y')
    payload_base64 = payload.get('payload_base64')
    if not isinstance(chunk_x, int) or not isinstance(chunk_z, int):
        return None
    if dimension not in (None, 0):
        return None
    if not (min_chunk_x <= chunk_x <= max_chunk_x and min_chunk_z <= chunk_z <= max_chunk_z):
        return None
    if not isinstance(sub_chunk_count, int) or not isinstance(payload_base64, str):
        if not isinstance(subchunk_y, int) or not isinstance(payload_base64, str):
            return None
    try:
        packet_payload = base64.b64decode(payload_base64)
        if isinstance(subchunk_y, int):
            return (
                SubchunkRecord(
                    chunk_x=chunk_x,
                    chunk_z=chunk_z,
                    subchunk_y=subchunk_y,
                    payload=packet_payload,
                    uses_runtime_palette=True,
                    dimension_id=dimension if isinstance(dimension, int) else 0,
                    record_source='packet-cache',
                ),
            )
        if isinstance(sub_chunk_count, int):
            return tuple(
                iter_packet_subchunk_records(
                    chunk_x=chunk_x,
                    chunk_z=chunk_z,
                    sub_chunk_count=sub_chunk_count,
                    payload=packet_payload,
                )
            )
    except (binascii.Error, ChunkDecodeError):
        return None
    return None


def save_render_result(path: Path, result: RenderResult) -> None:
    _write_text_atomically_with_retry(
        path,
        json.dumps(asdict(result), indent=2, sort_keys=True) + '\n',
    )


def _write_text_atomically_with_retry(
    path: Path,
    text: str,
    *,
    attempts: int = 5,
    retry_delay_seconds: float = 0.2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN, errno.EBUSY}
    last_error: OSError | None = None
    for attempt in range(attempts):
        temporary_path = path.with_name(f'.{path.name}.{os.getpid()}.{attempt}.tmp')
        try:
            temporary_path.write_text(text, encoding='utf-8')
            temporary_path.replace(path)
            return
        except OSError as exc:
            last_error = exc
            try:
                temporary_path.unlink()
            except OSError:
                pass
            if exc.errno not in retryable_errnos or attempt == attempts - 1:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error


def _save_image_with_retry(
    image: Any,
    path: Path,
    *,
    attempts: int = 5,
    retry_delay_seconds: float = 0.2,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    retryable_errnos = {errno.EDEADLK, errno.EAGAIN, errno.EBUSY}
    last_error: OSError | None = None
    for attempt in range(attempts):
        temporary_path = path.with_name(f'.{path.stem}.{os.getpid()}.{attempt}{path.suffix}')
        try:
            image.save(temporary_path)
            temporary_path.replace(path)
            return
        except OSError as exc:
            last_error = exc
            try:
                temporary_path.unlink()
            except OSError:
                pass
            if exc.errno not in retryable_errnos or attempt == attempts - 1:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error


def _write_uncolored_blocks_report(
    path: Path,
    uncolored_blocks: dict[str, UncoloredBlockStats],
    *,
    generated_at: str,
    world_path: Path,
    render_min_x: int,
    render_max_x: int,
    render_min_z: int,
    render_max_z: int,
    sample_step: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_count = sum(stats.count for stats in uncolored_blocks.values())
    lines = [
        'Worldgen Uncolored Block Report',
        '================================',
        '',
        f'Generated: {generated_at}',
        f'World: {world_path.resolve()}',
        f'Render area: x {render_min_x}..{render_max_x}, z {render_min_z}..{render_max_z}',
        f'Sample step: {sample_step}',
        '',
        (
            'These blocks were found while scanning top visible terrain, but the renderer did not '
            'have a color for them. They were skipped instead of being drawn as default gray.'
        ),
        'Add colors in `_block_color()` in `worldgen/render.py`.',
        '',
        f'Unique uncolored block entries: {len(uncolored_blocks)}',
        f'Total sampled uncolored occurrences: {total_count}',
    ]

    if not uncolored_blocks:
        lines.extend(['', 'No uncolored blocks were encountered.'])
        _write_text_atomically_with_retry(path, '\n'.join(lines) + '\n')
        return

    for stats in sorted(uncolored_blocks.values(), key=lambda item: (-item.count, item.block_name)):
        lines.extend(
            [
                '',
                f'Block: {stats.block_name}',
                f'  Count: {stats.count}',
                f'  Y range: {_format_optional_int(stats.min_y)}..{_format_optional_int(stats.max_y)}',
                f'  Sources: {_format_counter(stats.sources)}',
                f'  Runtime IDs: {_format_int_set(stats.runtime_ids)}',
                f'  Storage indices: {_format_int_set(stats.storage_indices)}',
                f'  Bits per block: {_format_int_set(stats.bits_per_block_values)}',
                f'  Palette sizes: {_format_int_set(stats.palette_sizes)}',
                f'  Unique chunks: {len(stats.chunks)}',
                '  Samples:',
            ]
        )
        for sample in stats.samples:
            runtime_id = 'none' if sample.runtime_id is None else str(sample.runtime_id)
            lines.append(
                (
                    f'    x={sample.world_x}, y={sample.world_y}, z={sample.world_z}; '
                    f'chunk=({sample.chunk_x}, {sample.chunk_z}), subchunk_y={sample.subchunk_y}; '
                    f'local=({sample.local_x}, {sample.local_y}, {sample.local_z}); '
                    f'source={sample.source}; storage={sample.storage_index}; '
                    f'palette_index={sample.palette_index}; runtime_id={runtime_id}; '
                    f'bits={sample.bits_per_block}; palette_size={sample.palette_size}'
                )
            )

    _write_text_atomically_with_retry(path, '\n'.join(lines) + '\n')


def _format_optional_int(value: int | None) -> str:
    return 'unknown' if value is None else str(value)


def _format_int_set(values: set[int]) -> str:
    if not values:
        return 'none'
    return ', '.join(str(value) for value in sorted(values))


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return 'none'
    return ', '.join(f'{name}: {count}' for name, count in counter.most_common())


def _sampled_axis_size(min_value: int, max_value: int, sample_step: int) -> int:
    return ((max_value - min_value) // sample_step) + 1


def _top_block_world_bounds(
    top_blocks: dict[tuple[int, int], TopBlock],
    *,
    min_x: int,
    min_z: int,
    sample_step: int,
) -> tuple[int | None, int | None, int | None, int | None]:
    if not top_blocks:
        return (None, None, None, None)

    pixel_x_values = [pixel_x for pixel_x, _pixel_z in top_blocks]
    pixel_z_values = [pixel_z for _pixel_x, pixel_z in top_blocks]
    return (
        min_x + (min(pixel_x_values) * sample_step),
        min_x + (max(pixel_x_values) * sample_step),
        min_z + (min(pixel_z_values) * sample_step),
        min_z + (max(pixel_z_values) * sample_step),
    )


def _visible_image_world_bounds(
    image: Any,
    *,
    min_x: int,
    min_z: int,
    sample_step: int,
) -> tuple[int, int | None, int | None, int | None, int | None]:
    alpha = image.getchannel('A')
    visible_pixel_count = sum(alpha.histogram()[1:])
    bounds = alpha.getbbox()
    if bounds is None:
        return (0, None, None, None, None)

    left, top, right, bottom = bounds
    return (
        visible_pixel_count,
        min_x + (left * sample_step),
        min_x + ((right - 1) * sample_step),
        min_z + (top * sample_step),
        min_z + ((bottom - 1) * sample_step),
    )


def _map_completion_percent(colored_pixels: int, total_pixels: int) -> float:
    if total_pixels <= 0:
        return 0.0
    return round((colored_pixels / total_pixels) * 100, 6)


def _unfinished_points_report_path(image_path: Path) -> Path:
    if image_path.name == 'blackport_topdown.png':
        return image_path.with_name('unfinished_points.json')
    return image_path.with_name(f'{image_path.stem}_unfinished_points.json')


def _write_unfinished_points_report(
    path: Path,
    image: Any,
    *,
    generated_at: str,
    world_path: Path,
    render_min_x: int,
    render_max_x: int,
    render_min_z: int,
    render_max_z: int,
    sample_step: int,
    colored_pixels: int,
    total_pixels: int,
    completion_percent: float,
    colored_min_x: int | None,
    colored_max_x: int | None,
    colored_min_z: int | None,
    colored_max_z: int | None,
) -> tuple[int, int]:
    outer_bounds_reached = (
        colored_min_x == render_min_x
        and colored_max_x == render_max_x
        and colored_min_z == render_min_z
        and colored_max_z == render_max_z
    )
    enabled = (
        outer_bounds_reached
        and completion_percent >= UNFINISHED_POINTS_COMPLETION_THRESHOLD
    )
    reason = None
    if not outer_bounds_reached:
        reason = 'Rendered pixels do not reach the outer render bounds yet.'
    elif completion_percent < UNFINISHED_POINTS_COMPLETION_THRESHOLD:
        reason = (
            f'Map completion is below {UNFINISHED_POINTS_COMPLETION_THRESHOLD:.0f}%.'
        )

    groups: list[dict[str, int]] = []
    unfinished_point_count = 0
    if enabled:
        groups, unfinished_point_count = _unfinished_point_row_groups(
            image,
            min_x=render_min_x,
            min_z=render_min_z,
            sample_step=sample_step,
        )

    payload = {
        'generated_at': generated_at,
        'enabled': enabled,
        'reason': reason,
        'completion_threshold_percent': UNFINISHED_POINTS_COMPLETION_THRESHOLD,
        'completion_percent': completion_percent,
        'outer_bounds_reached': outer_bounds_reached,
        'world_path': str(world_path.resolve()),
        'render_bounds': {
            'min_x': render_min_x,
            'max_x': render_max_x,
            'min_z': render_min_z,
            'max_z': render_max_z,
        },
        'colored_bounds': {
            'min_x': colored_min_x,
            'max_x': colored_max_x,
            'min_z': colored_min_z,
            'max_z': colored_max_z,
        },
        'sample_step': sample_step,
        'total_pixels': total_pixels,
        'colored_pixels': colored_pixels,
        'unfinished_point_count': unfinished_point_count,
        'unfinished_group_count': len(groups),
        'group_format': 'row z with inclusive x_min/x_max runs',
        'groups': groups,
    }
    _write_text_atomically_with_retry(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + '\n',
    )
    return unfinished_point_count, len(groups)


def _unfinished_point_row_groups(
    image: Any,
    *,
    min_x: int,
    min_z: int,
    sample_step: int,
) -> tuple[list[dict[str, int]], int]:
    alpha = image.getchannel('A')
    pixels = alpha.load()
    if pixels is None:
        return ([], 0)

    width, height = alpha.size
    groups: list[dict[str, int]] = []
    unfinished_point_count = 0
    for pixel_z in range(height):
        run_start_x: int | None = None
        for pixel_x in range(width):
            is_unfinished = pixels[pixel_x, pixel_z] == 0
            if is_unfinished and run_start_x is None:
                run_start_x = pixel_x
            elif not is_unfinished and run_start_x is not None:
                run_count = pixel_x - run_start_x
                groups.append(
                    _unfinished_point_group(
                        pixel_z,
                        run_start_x,
                        pixel_x - 1,
                        count=run_count,
                        min_x=min_x,
                        min_z=min_z,
                        sample_step=sample_step,
                    )
                )
                unfinished_point_count += run_count
                run_start_x = None
        if run_start_x is not None:
            run_count = width - run_start_x
            groups.append(
                _unfinished_point_group(
                    pixel_z,
                    run_start_x,
                    width - 1,
                    count=run_count,
                    min_x=min_x,
                    min_z=min_z,
                    sample_step=sample_step,
                )
            )
            unfinished_point_count += run_count

    return groups, unfinished_point_count


def _unfinished_point_group(
    pixel_z: int,
    start_pixel_x: int,
    end_pixel_x: int,
    *,
    count: int,
    min_x: int,
    min_z: int,
    sample_step: int,
) -> dict[str, int]:
    return {
        'z': min_z + (pixel_z * sample_step),
        'x_min': min_x + (start_pixel_x * sample_step),
        'x_max': min_x + (end_pixel_x * sample_step),
        'count': count,
    }


def _collect_subchunk_top_blocks(
    top_blocks: dict[tuple[int, int], TopBlock],
    subchunk: DecodedSubchunk,
    uncolored_blocks: dict[str, UncoloredBlockStats],
    *,
    min_x: int,
    max_x: int,
    min_z: int,
    max_z: int,
    sample_step: int,
    pixel_keys: set[tuple[int, int]] | None = None,
) -> None:
    for local_z in range(16):
        world_z = (subchunk.chunk_z * 16) + local_z
        pixel_z = _sample_pixel(world_z, min_z, max_z, sample_step)
        if pixel_z is None:
            continue
        for local_x in range(16):
            world_x = (subchunk.chunk_x * 16) + local_x
            pixel_x = _sample_pixel(world_x, min_x, max_x, sample_step)
            if pixel_x is None:
                continue

            pixel_key = (pixel_x, pixel_z)
            if pixel_keys is not None and pixel_key not in pixel_keys:
                continue
            current_top_block = top_blocks.get(pixel_key)
            if current_top_block is not None and current_top_block.y >= subchunk.max_y:
                continue

            for local_y in range(15, -1, -1):
                block_info = subchunk.visible_block_info(local_x, local_y, local_z)
                if block_info is None:
                    continue
                block_name = _resolve_block_name_for_render(block_info.name)
                block_y = subchunk.min_y + local_y
                if _is_chunk_touch_marker(block_name, block_y):
                    continue
                if _is_non_rendering_block(block_name):
                    continue
                if _block_color(block_name) is None:
                    _record_uncolored_block(
                        uncolored_blocks,
                        subchunk,
                        block_info,
                        world_x=world_x,
                        world_y=block_y,
                        world_z=world_z,
                        local_x=local_x,
                        local_y=local_y,
                        local_z=local_z,
                    )
                    continue
                if current_top_block is None or block_y > current_top_block.y:
                    top_blocks[pixel_key] = TopBlock(y=block_y, block_name=block_name)
                break


def _collect_subchunk_fixed_y_blocks(
    top_blocks: dict[tuple[int, int], TopBlock],
    subchunk: DecodedSubchunk,
    uncolored_blocks: dict[str, UncoloredBlockStats],
    *,
    fixed_y: int,
    min_x: int,
    max_x: int,
    min_z: int,
    max_z: int,
    sample_step: int,
    pixel_keys: set[tuple[int, int]] | None = None,
) -> None:
    if not subchunk.min_y <= fixed_y <= subchunk.max_y:
        return

    local_y = fixed_y - subchunk.min_y
    for local_z in range(16):
        world_z = (subchunk.chunk_z * 16) + local_z
        pixel_z = _sample_pixel(world_z, min_z, max_z, sample_step)
        if pixel_z is None:
            continue
        for local_x in range(16):
            world_x = (subchunk.chunk_x * 16) + local_x
            pixel_x = _sample_pixel(world_x, min_x, max_x, sample_step)
            if pixel_x is None:
                continue

            pixel_key = (pixel_x, pixel_z)
            if pixel_keys is not None and pixel_key not in pixel_keys:
                continue
            if pixel_key in top_blocks:
                continue

            block_info = subchunk.visible_block_info(local_x, local_y, local_z)
            if block_info is None:
                continue
            block_name = _resolve_block_name_for_render(block_info.name)
            if _is_non_rendering_block(block_name):
                continue
            if _block_color(block_name) is None:
                _record_uncolored_block(
                    uncolored_blocks,
                    subchunk,
                    block_info,
                    world_x=world_x,
                    world_y=fixed_y,
                    world_z=world_z,
                    local_x=local_x,
                    local_y=local_y,
                    local_z=local_z,
                )
                continue
            top_blocks[pixel_key] = TopBlock(y=fixed_y, block_name=block_name)


def _record_uncolored_block(
    uncolored_blocks: dict[str, UncoloredBlockStats],
    subchunk: DecodedSubchunk,
    block_info: BlockInfo,
    *,
    world_x: int,
    world_y: int,
    world_z: int,
    local_x: int,
    local_y: int,
    local_z: int,
) -> None:
    stats = uncolored_blocks.setdefault(
        block_info.name,
        UncoloredBlockStats(block_name=block_info.name),
    )
    stats.count += 1
    stats.min_y = world_y if stats.min_y is None else min(stats.min_y, world_y)
    stats.max_y = world_y if stats.max_y is None else max(stats.max_y, world_y)
    source = 'runtime-palette' if subchunk.uses_runtime_palette else 'leveldb-palette'
    stats.sources[source] += 1
    if block_info.runtime_id is not None:
        stats.runtime_ids.add(block_info.runtime_id)
    stats.storage_indices.add(block_info.storage_index)
    stats.bits_per_block_values.add(block_info.bits_per_block)
    stats.palette_sizes.add(block_info.palette_size)
    stats.chunks.add((subchunk.chunk_x, subchunk.chunk_z))
    if len(stats.samples) >= 12:
        return
    stats.samples.append(
        UncoloredBlockSample(
            world_x=world_x,
            world_y=world_y,
            world_z=world_z,
            chunk_x=subchunk.chunk_x,
            chunk_z=subchunk.chunk_z,
            subchunk_y=subchunk.subchunk_y,
            local_x=local_x,
            local_y=local_y,
            local_z=local_z,
            source=source,
            storage_index=block_info.storage_index,
            palette_index=block_info.palette_index,
            runtime_id=block_info.runtime_id,
            bits_per_block=block_info.bits_per_block,
            palette_size=block_info.palette_size,
        )
    )


def _subchunk_could_improve_top_blocks(
    top_blocks: dict[tuple[int, int], TopBlock],
    record: SubchunkRecord,
    *,
    min_x: int,
    max_x: int,
    min_z: int,
    max_z: int,
    sample_step: int,
    pixel_keys: set[tuple[int, int]] | None = None,
) -> bool:
    subchunk_max_y = (record.subchunk_y * 16) + 15
    for local_z in range(16):
        world_z = (record.chunk_z * 16) + local_z
        pixel_z = _sample_pixel(world_z, min_z, max_z, sample_step)
        if pixel_z is None:
            continue
        for local_x in range(16):
            world_x = (record.chunk_x * 16) + local_x
            pixel_x = _sample_pixel(world_x, min_x, max_x, sample_step)
            if pixel_x is None:
                continue

            pixel_key = (pixel_x, pixel_z)
            if pixel_keys is not None and pixel_key not in pixel_keys:
                continue
            current_top_block = top_blocks.get(pixel_key)
            if current_top_block is None or current_top_block.y < subchunk_max_y:
                return True
    return False


def _sample_pixel(value: int, min_value: int, max_value: int, sample_step: int) -> int | None:
    if value < min_value or value > max_value:
        return None
    offset = value - min_value
    if offset % sample_step != 0:
        return None
    return offset // sample_step


def _is_chunk_touch_marker(block_name: str, block_y: int) -> bool:
    return block_y <= CHUNK_TOUCH_MARKER_Y and block_name.strip().lower() in CHUNK_TOUCH_MARKER_BLOCKS


def _resolve_block_name_for_render(block_name: str) -> str:
    name = block_name.removeprefix('minecraft:').lower()
    if not name:
        return name
    if name.startswith('unknown_runtime_'):
        runtime_id_text = name.removeprefix('unknown_runtime_')
        try:
            runtime_id = int(runtime_id_text)
        except ValueError:
            return name
        resolved = UNKNOWN_RUNTIME_ID_BLOCK_OVERRIDES.get(runtime_id)
        if resolved is not None:
            return resolved.removeprefix('minecraft:').lower()
        return name
    alias = BLOCK_COLOR_ALIASES.get(name)
    if alias is not None:
        return alias
    return name


def _is_non_rendering_block(block_name: str) -> bool:
    return block_name in {'air', 'cave_air', 'void_air'}


def _block_color(block_name: str) -> tuple[int, int, int] | None:
    name = _resolve_block_name_for_render(block_name)
    if not name or name == 'unknown' or name.startswith('unknown_runtime_'):
        return None
    direct_color = BLOCK_COLOR_MAP.get(name)
    if direct_color is not None or name in BLOCK_COLOR_MAP:
        return direct_color
    if name.endswith('_leaves'):
        return BLOCK_COLOR_MAP['leaves']
    if name.endswith('_log') or name.endswith('_wood') or name.endswith('_planks'):
        family_alias = BLOCK_COLOR_ALIASES.get(name)
        if family_alias is not None and family_alias in BLOCK_COLOR_MAP:
            return BLOCK_COLOR_MAP[family_alias]
    if name.startswith('waxed_') and 'copper' in name:
        return BLOCK_COLOR_MAP['copper_block']
    if name.startswith('deepslate_') and name.endswith('_ore'):
        return BLOCK_COLOR_MAP['deepslate']
    if name.endswith('_ore'):
        return BLOCK_COLOR_MAP['stone']
    if 'water' in name or 'kelp' in name or 'seagrass' in name or name == 'bubble_column':
        return BLOCK_COLOR_MAP['water']
    if 'lava' in name or 'magma' in name:
        return BLOCK_COLOR_MAP['lava']
    if 'snow' in name:
        return BLOCK_COLOR_MAP['snow']
    if 'ice' in name:
        return BLOCK_COLOR_MAP['ice']
    if 'grass' in name or 'moss' in name or 'vine' in name:
        return BLOCK_COLOR_MAP['grass_block']
    if 'leaves' in name or 'azalea' in name:
        return BLOCK_COLOR_MAP['leaves']
    if 'sand' in name or 'sponge' in name or 'end_stone' in name:
        return BLOCK_COLOR_MAP['sand']
    if 'dirt' in name or 'mud' in name or 'farmland' in name or 'podzol' in name:
        return (126, 91, 58)
    if 'log' in name or 'wood' in name or 'planks' in name or 'stem' in name or 'hyphae' in name:
        return BLOCK_COLOR_MAP['oak_planks']
    if 'terracotta' in name or 'clay' in name or 'brick' in name:
        return BLOCK_COLOR_MAP['terracotta']
    if 'netherrack' in name or 'nylium' in name or 'wart' in name:
        return BLOCK_COLOR_MAP['netherrack']
    if 'deepslate' in name or 'blackstone' in name or 'bedrock' in name:
        return BLOCK_COLOR_MAP['deepslate']
    if (
        'stone' in name
        or 'ore' in name
        or 'andesite' in name
        or 'diorite' in name
        or 'granite' in name
        or 'tuff' in name
        or 'gravel' in name
        or 'basalt' in name
    ):
        return BLOCK_COLOR_MAP['stone']
    if 'wool' in name or 'concrete' in name:
        return (156, 158, 164)
    return None


def _draw_no_chunks_message(image: Any) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    text_lines = (
        'No generated chunks found',
        'Run the headless chunk loader,',
        'then render the saved world again.',
    )
    x = 24
    y = 24
    line_height = 18
    for index, line in enumerate(text_lines):
        draw.text((x, y + (index * line_height)), line, fill=(230, 234, 238))
