import random
import logging
from itertools import chain
from Fill import ShuffleError
from collections import OrderedDict
from Playthrough import Playthrough
from Region import TimeOfDay
from Rules import set_entrances_based_rules
from Entrance import Entrance
from State import State
from Item import ItemFactory
from Hints import get_hint_area


def set_all_entrances_data(world):
    for type, forward_entry, *return_entry in entrance_shuffle_table:
        forward_entrance = world.get_entrance(forward_entry[0])
        forward_entrance.data = forward_entry[1]
        forward_entrance.type = type
        forward_entrance.primary = True
        if type == 'Grotto':
            forward_entrance.data['index'] = 0x1000 + forward_entrance.data['grotto_id']
        if return_entry:
            return_entry = return_entry[0]
            return_entrance = world.get_entrance(return_entry[0])
            return_entrance.data = return_entry[1]
            return_entrance.type = type
            forward_entrance.bind_two_way(return_entrance)
            if type == 'Grotto':
                return_entrance.data['index'] = 0x2000 + return_entrance.data['grotto_id']


def assume_entrance_pool(entrance_pool):
    assumed_pool = []
    for entrance in entrance_pool:
        assumed_forward = entrance.assume_reachable()
        if entrance.reverse != None and not entrance.world.decouple_entrances:
            assumed_return = entrance.reverse.assume_reachable()
            world = entrance.world
            if not (world.mix_entrance_pools and (world.shuffle_overworld_entrances or world.shuffle_special_interior_entrances)):
                if (entrance.type in ('Dungeon', 'Grotto', 'Grave') and entrance.reverse.name != 'Spirit Temple Lobby -> Desert Colossus From Spirit Lobby') or \
                   (entrance.type == 'Interior' and world.shuffle_special_interior_entrances):
                    assumed_return.set_rule(lambda state, **kwargs: False)
            assumed_forward.bind_two_way(assumed_return)
        assumed_pool.append(assumed_forward)
    return assumed_pool


def build_one_way_targets(world, types_to_include, exclude=[]):
    one_way_entrances = []
    for pool_type in types_to_include:
        one_way_entrances += world.get_shufflable_entrances(type=pool_type)
    valid_one_way_entrances = list(filter(lambda entrance: entrance.name not in exclude and (entrance.shuffled or entrance.type not in ('OwlDrop', 'WarpSong', 'Spawn')), one_way_entrances))
    return [entrance.get_new_target() for entrance in valid_one_way_entrances]


entrance_shuffle_table = [
    ('Dungeon',         ('Outside Deku Tree -> Deku Tree Lobby',                            { 'index': 0x0000 }),
                        ('Deku Tree Lobby -> Outside Deku Tree',                            { 'index': 0x0209, 'blue_warp': 0x0457 })),
    ('Dungeon',         ('Death Mountain -> Dodongos Cavern Beginning',                     { 'index': 0x0004 }),
                        ('Dodongos Cavern Beginning -> Death Mountain',                     { 'index': 0x0242, 'blue_warp': 0x047A })),
    ('Dungeon',         ('Zoras Fountain -> Jabu Jabus Belly Beginning',                    { 'index': 0x0028 }),
                        ('Jabu Jabus Belly Beginning -> Zoras Fountain',                    { 'index': 0x0221, 'blue_warp': 0x010E })),
    ('Dungeon',         ('Forest Temple Entrance Ledge -> Forest Temple Lobby',             { 'index': 0x0169 }),
                        ('Forest Temple Lobby -> Forest Temple Entrance Ledge',             { 'index': 0x0215, 'blue_warp': 0x0608 })),
    ('Dungeon',         ('Fire Temple Entrance -> Fire Temple Lower',                       { 'index': 0x0165 }),
                        ('Fire Temple Lower -> Fire Temple Entrance',                       { 'index': 0x024A, 'blue_warp': 0x0564 })),
    ('Dungeon',         ('Lake Hylia -> Water Temple Lobby',                                { 'index': 0x0010 }),
                        ('Water Temple Lobby -> Lake Hylia',                                { 'index': 0x021D, 'blue_warp': 0x060C })),
    ('Dungeon',         ('Desert Colossus -> Spirit Temple Lobby',                          { 'index': 0x0082 }),
                        ('Spirit Temple Lobby -> Desert Colossus From Spirit Lobby',        { 'index': 0x01E1, 'blue_warp': 0x0610 })),
    ('Dungeon',         ('Shadow Temple Warp Region -> Shadow Temple Entryway',             { 'index': 0x0037 }),
                        ('Shadow Temple Entryway -> Shadow Temple Warp Region',             { 'index': 0x0205, 'blue_warp': 0x0580 })),
    ('Dungeon',         ('Kakariko Village -> Bottom of the Well',                          { 'index': 0x0098 }),
                        ('Bottom of the Well -> Kakariko Village',                          { 'index': 0x02A6 })),
    ('Dungeon',         ('Zoras Fountain Ice Ledge -> Ice Cavern Beginning',                { 'index': 0x0088 }),
                        ('Ice Cavern Beginning -> Zoras Fountain Ice Ledge',                { 'index': 0x03D4 })),
    ('Dungeon',         ('Gerudo Fortress -> Gerudo Training Grounds Lobby',                { 'index': 0x0008 }),
                        ('Gerudo Training Grounds Lobby -> Gerudo Fortress',                { 'index': 0x03A8 })),

    ('Interior',        ('Kokiri Forest -> Mido House',                                     { 'index': 0x0433 }),
                        ('Mido House -> Kokiri Forest',                                     { 'index': 0x0443 })),
    ('Interior',        ('Kokiri Forest -> Saria House',                                    { 'index': 0x0437 }),
                        ('Saria House -> Kokiri Forest',                                    { 'index': 0x0447 })),
    ('Interior',        ('Kokiri Forest -> House of Twins',                                 { 'index': 0x009C }),
                        ('House of Twins -> Kokiri Forest',                                 { 'index': 0x033C })),
    ('Interior',        ('Kokiri Forest -> Know It All House',                              { 'index': 0x00C9 }),
                        ('Know It All House -> Kokiri Forest',                              { 'index': 0x026A })),
    ('Interior',        ('Kokiri Forest -> Kokiri Shop',                                    { 'index': 0x00C1 }),
                        ('Kokiri Shop -> Kokiri Forest',                                    { 'index': 0x0266 })),
    ('Interior',        ('Lake Hylia -> Lake Hylia Lab',                                    { 'index': 0x0043 }),
                        ('Lake Hylia Lab -> Lake Hylia',                                    { 'index': 0x03CC })),
    ('Interior',        ('Lake Hylia Fishing Island -> Fishing Hole',                       { 'index': 0x045F }),
                        ('Fishing Hole -> Lake Hylia Fishing Island',                       { 'index': 0x0309 })),
    ('Interior',        ('Gerudo Valley Far Side -> Carpenter Tent',                        { 'index': 0x03A0 }),
                        ('Carpenter Tent -> Gerudo Valley Far Side',                        { 'index': 0x03D0 })),
    ('Interior',        ('Castle Town Entrance -> Castle Town Rupee Room',                  { 'index': 0x007E }),
                        ('Castle Town Rupee Room -> Castle Town Entrance',                  { 'index': 0x026E })),
    ('Interior',        ('Castle Town -> Castle Town Mask Shop',                            { 'index': 0x0530 }),
                        ('Castle Town Mask Shop -> Castle Town',                            { 'index': 0x01D1, 'addresses': [0xC6DA5E] })),
    ('Interior',        ('Castle Town -> Castle Town Bombchu Bowling',                      { 'index': 0x0507 }),
                        ('Castle Town Bombchu Bowling -> Castle Town',                      { 'index': 0x03BC })),
    ('Interior',        ('Castle Town -> Castle Town Potion Shop',                          { 'index': 0x0388 }),
                        ('Castle Town Potion Shop -> Castle Town',                          { 'index': 0x02A2 })),
    ('Interior',        ('Castle Town -> Castle Town Treasure Chest Game',                  { 'index': 0x0063 }),
                        ('Castle Town Treasure Chest Game -> Castle Town',                  { 'index': 0x01D5 })),
    ('Interior',        ('Castle Town Back Alley -> Castle Town Bombchu Shop',              { 'index': 0x0528 }),
                        ('Castle Town Bombchu Shop -> Castle Town Back Alley',              { 'index': 0x03C0 })),
    ('Interior',        ('Castle Town Back Alley -> Castle Town Man in Green House',        { 'index': 0x043B }),
                        ('Castle Town Man in Green House -> Castle Town Back Alley',        { 'index': 0x0067 })),
    ('Interior',        ('Kakariko Village -> Carpenter Boss House',                        { 'index': 0x02FD }),
                        ('Carpenter Boss House -> Kakariko Village',                        { 'index': 0x0349 })),
    ('Interior',        ('Kakariko Village -> House of Skulltula',                          { 'index': 0x0550 }),
                        ('House of Skulltula -> Kakariko Village',                          { 'index': 0x04EE })),
    ('Interior',        ('Kakariko Village -> Impas House',                                 { 'index': 0x039C }),
                        ('Impas House -> Kakariko Village',                                 { 'index': 0x0345 })),
    ('Interior',        ('Kakariko Impa Ledge -> Impas House Back',                         { 'index': 0x05C8 }),
                        ('Impas House Back -> Kakariko Impa Ledge',                         { 'index': 0x05DC })),
    ('Interior',        ('Kakariko Village Backyard -> Odd Medicine Building',              { 'index': 0x0072 }),
                        ('Odd Medicine Building -> Kakariko Village Backyard',              { 'index': 0x034D })),
    ('Interior',        ('Graveyard -> Dampes House',                                       { 'index': 0x030D }),
                        ('Dampes House -> Graveyard',                                       { 'index': 0x0355 })),
    ('Interior',        ('Goron City -> Goron Shop',                                        { 'index': 0x037C }),
                        ('Goron Shop -> Goron City',                                        { 'index': 0x03FC })),
    ('Interior',        ('Zoras Domain -> Zora Shop',                                       { 'index': 0x0380 }),
                        ('Zora Shop -> Zoras Domain',                                       { 'index': 0x03C4 })),
    ('Interior',        ('Lon Lon Ranch -> Talon House',                                    { 'index': 0x004F }),
                        ('Talon House -> Lon Lon Ranch',                                    { 'index': 0x0378 })),
    ('Interior',        ('Lon Lon Ranch -> Ingo Barn',                                      { 'index': 0x02F9 }),
                        ('Ingo Barn -> Lon Lon Ranch',                                      { 'index': 0x042F })),
    ('Interior',        ('Lon Lon Ranch -> Lon Lon Corner Tower',                           { 'index': 0x05D0 }),
                        ('Lon Lon Corner Tower -> Lon Lon Ranch',                           { 'index': 0x05D4 })),
    ('Interior',        ('Castle Town -> Castle Town Bazaar',                               { 'index': 0x052C }),
                        ('Castle Town Bazaar -> Castle Town',                               { 'index': 0x03B8, 'addresses': [0xBEFD74] })),
    ('Interior',        ('Castle Town -> Castle Town Shooting Gallery',                     { 'index': 0x016D }),
                        ('Castle Town Shooting Gallery -> Castle Town',                     { 'index': 0x01CD, 'addresses': [0xBEFD7C] })),
    ('Interior',        ('Kakariko Village -> Kakariko Bazaar',                             { 'index': 0x00B7 }),
                        ('Kakariko Bazaar -> Kakariko Village',                             { 'index': 0x0201, 'addresses': [0xBEFD72] })),
    ('Interior',        ('Kakariko Village -> Kakariko Shooting Gallery',                   { 'index': 0x003B }),
                        ('Kakariko Shooting Gallery -> Kakariko Village',                   { 'index': 0x0463, 'addresses': [0xBEFD7A] })),
    ('Interior',        ('Desert Colossus -> Colossus Fairy',                               { 'index': 0x0588 }),
                        ('Colossus Fairy -> Desert Colossus',                               { 'index': 0x057C, 'addresses': [0xBEFD82] })),
    ('Interior',        ('Hyrule Castle Grounds -> Hyrule Castle Fairy',                    { 'index': 0x0578 }),
                        ('Hyrule Castle Fairy -> Castle Grounds',                           { 'index': 0x0340, 'addresses': [0xBEFD80] })),
    ('Interior',        ('Ganons Castle Grounds -> Ganons Castle Fairy',                    { 'index': 0x04C2 }),
                        ('Ganons Castle Fairy -> Castle Grounds',                           { 'index': 0x0340, 'addresses': [0xBEFD6C] })),
    ('Interior',        ('Death Mountain Crater Lower Nearby -> Crater Fairy',              { 'index': 0x04BE }),
                        ('Crater Fairy -> Death Mountain Crater Lower Local',               { 'index': 0x0482, 'addresses': [0xBEFD6A] })),
    ('Interior',        ('Death Mountain Summit -> Mountain Summit Fairy',                  { 'index': 0x0315 }),
                        ('Mountain Summit Fairy -> Death Mountain Summit',                  { 'index': 0x045B, 'addresses': [0xBEFD68] })),
    ('Interior',        ('Zoras Fountain -> Zoras Fountain Fairy',                          { 'index': 0x0371 }),
                        ('Zoras Fountain Fairy -> Zoras Fountain',                          { 'index': 0x0394, 'addresses': [0xBEFD7E] })),

    ('SpecialInterior', ('Kokiri Forest -> Links House',                                    { 'index': 0x0272 }),
                        ('Links House -> Kokiri Forest',                                    { 'index': 0x0211 })),
    ('SpecialInterior', ('Temple of Time Exterior -> Temple of Time',                       { 'index': 0x0053 }),
                        ('Temple of Time -> Temple of Time Exterior',                       { 'index': 0x0472 })),
    ('SpecialInterior', ('Kakariko Village -> Windmill',                                    { 'index': 0x0453 }),
                        ('Windmill -> Kakariko Village',                                    { 'index': 0x0351 })),
    ('SpecialInterior', ('Kakariko Village -> Kakariko Potion Shop Front',                  { 'index': 0x0384 }),
                        ('Kakariko Potion Shop Front -> Kakariko Village',                  { 'index': 0x044B })),
    ('SpecialInterior', ('Kakariko Village Backyard -> Kakariko Potion Shop Back',          { 'index': 0x03EC }),
                        ('Kakariko Potion Shop Back -> Kakariko Village Backyard',          { 'index': 0x04FF })),

    ('Grotto',          ('Desert Colossus -> Desert Colossus Grotto',                       { 'grotto_id': 0x00, 'entrance': 0x05BC, 'content': 0xFD, 'scene': 0x5C }),
                        ('Desert Colossus Grotto -> Desert Colossus',                       { 'grotto_id': 0x00, 'entrance': 0x0123, 'room': 0x00, 'angle': 0xA71C, 'pos': (0x427A0800, 0xC2000000, 0xC4A20666) })),
    ('Grotto',          ('Lake Hylia -> Lake Hylia Grotto',                                 { 'grotto_id': 0x01, 'entrance': 0x05A4, 'content': 0xEF, 'scene': 0x57 }),
                        ('Lake Hylia Grotto -> Lake Hylia',                                 { 'grotto_id': 0x01, 'entrance': 0x0102, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC53DF56A, 0xC4812000, 0x45BE05F2) })),
    ('Grotto',          ('Zora River -> Zora River Storms Grotto',                          { 'grotto_id': 0x02, 'entrance': 0x05BC, 'content': 0xEB, 'scene': 0x54 }),
                        ('Zora River Storms Grotto -> Zora River',                          { 'grotto_id': 0x02, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC4CBC1B4, 0x42C80000, 0xC3041ABE) })),
    ('Grotto',          ('Zora River -> Zora River Plateau Bombable Grotto',                { 'grotto_id': 0x03, 'entrance': 0x036D, 'content': 0xE6, 'scene': 0x54 }),
                        ('Zora River Plateau Bombable Grotto -> Zora River',                { 'grotto_id': 0x03, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0xE000, 'pos': (0x4427A070, 0x440E8000, 0xC3B4ED3B) })),
    ('Grotto',          ('Zora River -> Zora River Plateau Open Grotto',                    { 'grotto_id': 0x04, 'entrance': 0x003F, 'content': 0x29, 'scene': 0x54 }),
                        ('Zora River Plateau Open Grotto -> Zora River',                    { 'grotto_id': 0x04, 'entrance': 0x00EA, 'room': 0x00, 'angle': 0x8000, 'pos': (0x43B52520, 0x440E8000, 0x4309A14F) })),
    ('Grotto',          ('Death Mountain Crater Lower Nearby -> DMC Hammer Grotto',         { 'grotto_id': 0x05, 'entrance': 0x05A4, 'content': 0xF9, 'scene': 0x61 }),
                        ('DMC Hammer Grotto -> Death Mountain Crater Lower Local',          { 'grotto_id': 0x05, 'entrance': 0x0246, 'room': 0x01, 'angle': 0x31C7, 'pos': (0xC4D290C0, 0x44348000, 0xC3ED5557) })),
    ('Grotto',          ('Death Mountain Crater Upper Nearby -> Top of Crater Grotto',      { 'grotto_id': 0x06, 'entrance': 0x003F, 'content': 0x7A, 'scene': 0x61 }),
                        ('Top of Crater Grotto -> Death Mountain Crater Upper Local',       { 'grotto_id': 0x06, 'entrance': 0x0147, 'room': 0x01, 'angle': 0x238E, 'pos': (0x420F3401, 0x449E2000, 0x44DCD549) })),
    ('Grotto',          ('Goron City Grotto Platform -> Goron City Grotto',                 { 'grotto_id': 0x07, 'entrance': 0x05A4, 'content': 0xFB, 'scene': 0x62 }),
                        ('Goron City Grotto -> Goron City Grotto Platform',                 { 'grotto_id': 0x07, 'entrance': 0x014D, 'room': 0x03, 'angle': 0x0000, 'pos': (0x448A1754, 0x44110000, 0xC493CCFD) })),
    ('Grotto',          ('Death Mountain -> Mountain Storms Grotto',                        { 'grotto_id': 0x08, 'entrance': 0x003F, 'content': 0x57, 'scene': 0x60 }),
                        ('Mountain Storms Grotto -> Death Mountain',                        { 'grotto_id': 0x08, 'entrance': 0x01B9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC3C1CAC1, 0x44AD4000, 0xC497A1BA) })),
    ('Grotto',          ('Death Mountain Summit -> Mountain Bombable Grotto',               { 'grotto_id': 0x09, 'entrance': 0x05FC, 'content': 0xF8, 'scene': 0x60 }),
                        ('Mountain Bombable Grotto -> Death Mountain Summit',               { 'grotto_id': 0x09, 'entrance': 0x01B9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC42CC164, 0x44F34000, 0xC38CFC0C) })),
    ('Grotto',          ('Kakariko Village Backyard -> Kakariko Back Grotto',               { 'grotto_id': 0x0A, 'entrance': 0x003F, 'content': 0x28, 'scene': 0x52 }),
                        ('Kakariko Back Grotto -> Kakariko Village Backyard',               { 'grotto_id': 0x0A, 'entrance': 0x00DB, 'room': 0x00, 'angle': 0x0000, 'pos': (0x4455CF3B, 0x42A00000, 0xC37D1871) })),
    ('Grotto',          ('Kakariko Village -> Kakariko Bombable Grotto',                    { 'grotto_id': 0x0B, 'entrance': 0x05A0, 'content': 0xE7, 'scene': 0x52 }),
                        ('Kakariko Bombable Grotto -> Kakariko Village',                    { 'grotto_id': 0x0B, 'entrance': 0x00DB, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC3C8EFCE, 0x00000000, 0x43C96551) })),
    ('Grotto',          ('Hyrule Castle Grounds -> Castle Storms Grotto',                   { 'grotto_id': 0x0C, 'entrance': 0x05B8, 'content': 0xF6, 'scene': 0x5F }),
                        ('Castle Storms Grotto -> Castle Grounds',                          { 'grotto_id': 0x0C, 'entrance': 0x0138, 'room': 0x00, 'angle': 0x9555, 'pos': (0x447C4104, 0x44C46000, 0x4455E211) })),
    ('Grotto',          ('Hyrule Field -> Field North Lon Lon Grotto',                      { 'grotto_id': 0x0D, 'entrance': 0x05C0, 'content': 0xE1, 'scene': 0x51 }),
                        ('Field North Lon Lon Grotto -> Hyrule Field',                      { 'grotto_id': 0x0D, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x1555, 'pos': (0xC59AACA0, 0xC3960000, 0x45315966) })),
    ('Grotto',          ('Hyrule Field -> Field Kakariko Grotto',                           { 'grotto_id': 0x0E, 'entrance': 0x0598, 'content': 0xE5, 'scene': 0x51 }),
                        ('Field Kakariko Grotto -> Hyrule Field',                           { 'grotto_id': 0x0E, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xC000, 'pos': (0x4500299B, 0x41A00000, 0xC32065BD) })),
    ('Grotto',          ('Hyrule Field -> Field Far West Castle Town Grotto',               { 'grotto_id': 0x0F, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x51 }),
                        ('Field Far West Castle Town Grotto -> Hyrule Field',               { 'grotto_id': 0x0F, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC58B2544, 0xC3960000, 0xC3D5186B) })),
    ('Grotto',          ('Hyrule Field -> Field West Castle Town Grotto',                   { 'grotto_id': 0x10, 'entrance': 0x003F, 'content': 0x00, 'scene': 0x51 }),
                        ('Field West Castle Town Grotto -> Hyrule Field',                   { 'grotto_id': 0x10, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xE000, 'pos': (0xC4B2B1F3, 0x00000000, 0x444C719D) })),
    ('Grotto',          ('Hyrule Field -> Field Valley Grotto',                             { 'grotto_id': 0x11, 'entrance': 0x05A8, 'content': 0xE4, 'scene': 0x51 }),
                        ('Field Valley Grotto -> Hyrule Field',                             { 'grotto_id': 0x11, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x0000, 'pos': (0xC5F61086, 0xC3960000, 0x45D84A7E) })),
    ('Grotto',          ('Hyrule Field -> Field Near Lake Inside Fence Grotto',             { 'grotto_id': 0x12, 'entrance': 0x059C, 'content': 0xE6, 'scene': 0x51 }),
                        ('Field Near Lake Inside Fence Grotto -> Hyrule Field',             { 'grotto_id': 0x12, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0xEAAB, 'pos': (0xC59BE902, 0xC42F0000, 0x4657F479) })),
    ('Grotto',          ('Hyrule Field -> Field Near Lake Outside Fence Grotto',            { 'grotto_id': 0x13, 'entrance': 0x003F, 'content': 0x03, 'scene': 0x51 }),
                        ('Field Near Lake Outside Fence Grotto -> Hyrule Field',            { 'grotto_id': 0x13, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC57B69B1, 0xC42F0000, 0x46588DF2) })),
    ('Grotto',          ('Hyrule Field -> Remote Southern Grotto',                          { 'grotto_id': 0x14, 'entrance': 0x003F, 'content': 0x22, 'scene': 0x51 }),
                        ('Remote Southern Grotto -> Hyrule Field',                          { 'grotto_id': 0x14, 'entrance': 0x01F9, 'room': 0x00, 'angle': 0x9555, 'pos': (0xC384A807, 0xC3FA0000, 0x4640DCC8) })),
    ('Grotto',          ('Lon Lon Ranch -> Lon Lon Grotto',                                 { 'grotto_id': 0x15, 'entrance': 0x05A4, 'content': 0xFC, 'scene': 0x63 }),
                        ('Lon Lon Grotto -> Lon Lon Ranch',                                 { 'grotto_id': 0x15, 'entrance': 0x0157, 'room': 0x00, 'angle': 0xAAAB, 'pos': (0x44E0FD92, 0x00000000, 0x44BB9A4C) })),
    ('Grotto',          ('Sacred Forest Meadow Entryway -> Front of Meadow Grotto',         { 'grotto_id': 0x16, 'entrance': 0x05B4, 'content': 0xED, 'scene': 0x56 }),
                        ('Front of Meadow Grotto -> Sacred Forest Meadow Entryway',         { 'grotto_id': 0x16, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0x8000, 'pos': (0xC33DDC64, 0x00000000, 0x44ED42CE) })),
    ('Grotto',          ('Sacred Forest Meadow -> Meadow Storms Grotto',                    { 'grotto_id': 0x17, 'entrance': 0x05BC, 'content': 0xEE, 'scene': 0x56 }),
                        ('Meadow Storms Grotto -> Sacred Forest Meadow',                    { 'grotto_id': 0x17, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0xAAAB, 'pos': (0x439D6D22, 0x43F00000, 0xC50FC63A) })),
    ('Grotto',          ('Sacred Forest Meadow -> Meadow Fairy Grotto',                     { 'grotto_id': 0x18, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x56 }),
                        ('Meadow Fairy Grotto -> Sacred Forest Meadow',                     { 'grotto_id': 0x18, 'entrance': 0x00FC, 'room': 0x00, 'angle': 0x0000, 'pos': (0x425C22D1, 0x00000000, 0x434E9835) })),
    ('Grotto',          ('Lost Woods Beyond Mido -> Lost Woods Sales Grotto',               { 'grotto_id': 0x19, 'entrance': 0x05B0, 'content': 0xF5, 'scene': 0x5B }),
                        ('Lost Woods Sales Grotto -> Lost Woods Beyond Mido',               { 'grotto_id': 0x19, 'entrance': 0x01A9, 'room': 0x08, 'angle': 0x2000, 'pos': (0x44293FA2, 0x00000000, 0xC51DE32B) })),
    ('Grotto',          ('Lost Woods -> Lost Woods Generic Grotto',                         { 'grotto_id': 0x1A, 'entrance': 0x003F, 'content': 0x14, 'scene': 0x5B }),
                        ('Lost Woods Generic Grotto -> Lost Woods',                         { 'grotto_id': 0x1A, 'entrance': 0x011E, 'room': 0x02, 'angle': 0xE000, 'pos': (0x4464B055, 0x00000000, 0xC464DB7D) })),
    ('Grotto',          ('Kokiri Forest -> Kokiri Forest Storms Grotto',                    { 'grotto_id': 0x1B, 'entrance': 0x003F, 'content': 0x2C, 'scene': 0x55 }),
                        ('Kokiri Forest Storms Grotto -> Kokiri Forest',                    { 'grotto_id': 0x1B, 'entrance': 0x0286, 'room': 0x00, 'angle': 0x4000, 'pos': (0xC3FD8856, 0x43BE0000, 0xC4988DA8) })),
    ('Grotto',          ('Zoras Domain -> Zoras Domain Storms Grotto',                      { 'grotto_id': 0x1C, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x58 }),
                        ('Zoras Domain Storms Grotto -> Zoras Domain',                      { 'grotto_id': 0x1C, 'entrance': 0x0108, 'room': 0x01, 'angle': 0xD555, 'pos': (0xC455EB8D, 0x41600000, 0xC3ED3602) })),
    ('Grotto',          ('Gerudo Fortress -> Gerudo Fortress Storms Grotto',                { 'grotto_id': 0x1D, 'entrance': 0x036D, 'content': 0xFF, 'scene': 0x5D }),
                        ('Gerudo Fortress Storms Grotto -> Gerudo Fortress',                { 'grotto_id': 0x1D, 'entrance': 0x0129, 'room': 0x00, 'angle': 0x4000, 'pos': (0x43BE42C0, 0x43A68000, 0xC4C317B1) })),
    ('Grotto',          ('Gerudo Valley Far Side -> Gerudo Valley Storms Grotto',           { 'grotto_id': 0x1E, 'entrance': 0x05BC, 'content': 0xF0, 'scene': 0x5A }),
                        ('Gerudo Valley Storms Grotto -> Gerudo Valley Far Side',           { 'grotto_id': 0x1E, 'entrance': 0x022D, 'room': 0x00, 'angle': 0x9555, 'pos': (0xC4A5CAD2, 0x41700000, 0xC475FF9B) })),
    ('Grotto',          ('Gerudo Valley Grotto Ledge -> Gerudo Valley Octorok Grotto',      { 'grotto_id': 0x1F, 'entrance': 0x05AC, 'content': 0xF2, 'scene': 0x5A }),
                        ('Gerudo Valley Octorok Grotto -> Gerudo Valley Grotto Ledge',      { 'grotto_id': 0x1F, 'entrance': 0x0117, 'room': 0x00, 'angle': 0x8000, 'pos': (0x4391C1A4, 0xC40AC000, 0x44B8CC9B) })),
    ('Grotto',          ('Lost Woods Beyond Mido -> Deku Theater',                          { 'grotto_id': 0x20, 'entrance': 0x05C4, 'content': 0xF3, 'scene': 0x5B }),
                        ('Deku Theater -> Lost Woods Beyond Mido',                          { 'grotto_id': 0x20, 'entrance': 0x01A9, 'room': 0x06, 'angle': 0x4000, 'pos': (0x42AA8FDA, 0xC1A00000, 0xC4C82D49) })),

    ('Grave',           ('Graveyard -> Shield Grave',                                       { 'index': 0x004B }),
                        ('Shield Grave -> Graveyard',                                       { 'index': 0x035D })),
    ('Grave',           ('Graveyard -> Heart Piece Grave',                                  { 'index': 0x031C }),
                        ('Heart Piece Grave -> Graveyard',                                  { 'index': 0x0361 })),
    ('Grave',           ('Graveyard -> Composer Grave',                                     { 'index': 0x002D }),
                        ('Composer Grave -> Graveyard',                                     { 'index': 0x050B })),
    ('Grave',           ('Graveyard -> Dampes Grave',                                       { 'index': 0x044F }),
                        ('Dampes Grave -> Graveyard',                                       { 'index': 0x0359 })),

    ('Overworld',       ('Kokiri Forest -> Lost Woods Bridge From Forest',                  { 'index': 0x05E0 }),
                        ('Lost Woods Bridge -> Kokiri Forest',                              { 'index': 0x020D })),
    ('Overworld',       ('Kokiri Forest -> Lost Woods',                                     { 'index': 0x011E }),
                        ('Lost Woods Forest Exit -> Kokiri Forest',                         { 'index': 0x0286 })),
    ('Overworld',       ('Lost Woods -> Goron City Woods Warp',                             { 'index': 0x04E2 }),
                        ('Goron City Woods Warp -> Lost Woods',                             { 'index': 0x04D6 })),
    ('Overworld',       ('Lost Woods -> Zora River',                                        { 'index': 0x01DD }),
                        ('Zora River -> Lost Woods',                                        { 'index': 0x04DA })),
    ('Overworld',       ('Lost Woods Beyond Mido -> Sacred Forest Meadow Entryway',         { 'index': 0x00FC }),
                        ('Sacred Forest Meadow Entryway -> Lost Woods Beyond Mido',         { 'index': 0x01A9 })),
    ('Overworld',       ('Lost Woods Bridge -> Hyrule Field',                               { 'index': 0x0185 }),
                        ('Hyrule Field -> Lost Woods Bridge',                               { 'index': 0x04DE })),
    ('Overworld',       ('Hyrule Field -> Lake Hylia',                                      { 'index': 0x0102 }),
                        ('Lake Hylia -> Hyrule Field',                                      { 'index': 0x0189 })),
    ('Overworld',       ('Hyrule Field -> Gerudo Valley',                                   { 'index': 0x0117 }),
                        ('Gerudo Valley -> Hyrule Field',                                   { 'index': 0x018D })),
    ('Overworld',       ('Hyrule Field -> Castle Town Entrance',                            { 'index': 0x0276 }),
                        ('Castle Town Entrance -> Hyrule Field',                            { 'index': 0x01FD })),
    ('Overworld',       ('Hyrule Field -> Kakariko Village',                                { 'index': 0x00DB }),
                        ('Kakariko Village -> Hyrule Field',                                { 'index': 0x017D })),
    ('Overworld',       ('Hyrule Field -> Zora River Front',                                { 'index': 0x00EA }),
                        ('Zora River Front -> Hyrule Field',                                { 'index': 0x0181 })),
    ('Overworld',       ('Hyrule Field -> Lon Lon Ranch',                                   { 'index': 0x0157 }),
                        ('Lon Lon Ranch -> Hyrule Field',                                   { 'index': 0x01F9 })),
    ('Overworld',       ('Lake Hylia -> Zoras Domain',                                      { 'index': 0x0328 }),
                        ('Zoras Domain -> Lake Hylia',                                      { 'index': 0x0560 })),
    ('Overworld',       ('Gerudo Valley Far Side -> Gerudo Fortress',                       { 'index': 0x0129 }),
                        ('Gerudo Fortress -> Gerudo Valley Far Side',                       { 'index': 0x022D })),
    ('Overworld',       ('Gerudo Fortress Outside Gate -> Haunted Wasteland Near Fortress', { 'index': 0x0130 }),
                        ('Haunted Wasteland Near Fortress -> Gerudo Fortress Outside Gate', { 'index': 0x03AC })),
    ('Overworld',       ('Haunted Wasteland Near Colossus -> Desert Colossus',              { 'index': 0x0123 }),
                        ('Desert Colossus -> Haunted Wasteland Near Colossus',              { 'index': 0x0365 })),
    ('Overworld',       ('Castle Town Entrance -> Castle Town',                             { 'index': 0x00B1 }),
                        ('Castle Town -> Castle Town Entrance',                             { 'index': 0x0033 })),
    ('Overworld',       ('Castle Town -> Castle Grounds',                                   { 'index': 0x0138 }),
                        ('Castle Grounds -> Castle Town',                                   { 'index': 0x025A })),
    ('Overworld',       ('Castle Town -> Temple of Time Exterior',                          { 'index': 0x0171 }),
                        ('Temple of Time Exterior -> Castle Town',                          { 'index': 0x025E })),
    ('Overworld',       ('Kakariko Village -> Graveyard',                                   { 'index': 0x00E4 }),
                        ('Graveyard -> Kakariko Village',                                   { 'index': 0x0195 })),
    ('Overworld',       ('Kakariko Village Behind Gate -> Death Mountain',                  { 'index': 0x013D }),
                        ('Death Mountain -> Kakariko Village Behind Gate',                  { 'index': 0x0191 })),
    ('Overworld',       ('Death Mountain -> Goron City',                                    { 'index': 0x014D }),
                        ('Goron City -> Death Mountain',                                    { 'index': 0x01B9 })),
    ('Overworld',       ('Darunias Chamber -> Death Mountain Crater Lower Local',           { 'index': 0x0246 }),
                        ('Death Mountain Crater Lower Nearby -> Darunias Chamber',          { 'index': 0x01C1 })),
    ('Overworld',       ('Death Mountain Summit -> Death Mountain Crater Upper Local',      { 'index': 0x0147 }),
                        ('Death Mountain Crater Upper Nearby -> Death Mountain Summit',     { 'index': 0x01BD })),
    ('Overworld',       ('Zora River Behind Waterfall -> Zoras Domain',                     { 'index': 0x0108 }),
                        ('Zoras Domain -> Zora River Behind Waterfall',                     { 'index': 0x019D })),
    ('Overworld',       ('Zoras Domain Behind King Zora -> Zoras Fountain',                 { 'index': 0x0225 }),
                        ('Zoras Fountain -> Zoras Domain Behind King Zora',                 { 'index': 0x01A1 })),

    ('OwlDrop',         ('Lake Hylia Owl Flight -> Hyrule Field',                           { 'index': 0x027E, 'addresses': [0xAC9F26] })),
    ('OwlDrop',         ('Death Mountain Owl Flight -> Kakariko Impa Ledge',                { 'index': 0x0554, 'addresses': [0xAC9EF2] })),

    ('Spawn',           ('Child Spawn -> Links House',                                      { 'index': 0x00BB, 'addresses': [0xB0631E, 0xB06342] })),
    ('Spawn',           ('Adult Spawn -> Temple of Time',                                   { 'index': 0x05F4, 'addresses': [0xB06332] })),

    ('WarpSong',        ('Minuet of Forest Warp -> Sacred Forest Meadow',                   { 'index': 0x0600, 'addresses': [0xBF023C] })),
    ('WarpSong',        ('Bolero of Fire Warp -> Death Mountain Crater Central Local',      { 'index': 0x04F6, 'addresses': [0xBF023E] })),
    ('WarpSong',        ('Serenade of Water Warp -> Lake Hylia',                            { 'index': 0x0604, 'addresses': [0xBF0240] })),
    ('WarpSong',        ('Requiem of Spirit Warp -> Desert Colossus',                       { 'index': 0x01F1, 'addresses': [0xBF0242] })),
    ('WarpSong',        ('Nocturne of Shadow Warp -> Shadow Temple Warp Region',            { 'index': 0x0568, 'addresses': [0xBF0244] })),
    ('WarpSong',        ('Prelude of Light Warp -> Temple of Time',                         { 'index': 0x05F4, 'addresses': [0xBF0246] })),

    ('Extra',           ('Lost Woods Mushroom Timeout -> Lost Woods',                       { 'index': 0x01AD })),
    ('Extra',           ('Zoras Domain Eyeball Frog Timeout -> Zoras Domain',               { 'index': 0x0153 })),
    ('Extra',           ('Zora River Top of Waterfall -> Zora River',                       { 'index': 0x0199 })),
]


class EntranceShuffleError(ShuffleError):
    pass


# Set entrances of all worlds, first initializing them to their default regions, then potentially shuffling part of them
def set_entrances(worlds):
    for world in worlds:
        world.initialize_entrances()

    if worlds[0].entrance_shuffle:
        shuffle_random_entrances(worlds)

    set_entrances_based_rules(worlds)


# Shuffles entrances that need to be shuffled in all worlds
def shuffle_random_entrances(worlds):

    # Store all locations reachable before shuffling to differentiate which locations were already unreachable from those we made unreachable
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
    max_playthrough = Playthrough.max_explore([world.state for world in worlds], complete_itempool)

    non_drop_locations = [location for world in worlds for location in world.get_locations() if location.type not in ('Drop', 'Event')]
    max_playthrough.visit_locations(non_drop_locations)
    locations_to_ensure_reachable = list(filter(max_playthrough.visited, non_drop_locations))

    # Shuffle all entrances within their own worlds
    for world in worlds:
        # Set entrance data for all entrances, even those we aren't shuffling
        set_all_entrances_data(world)

        # Determine entrance pools based on settings, to be shuffled in the order we set them by
        one_way_entrance_pools = OrderedDict()
        entrance_pools = OrderedDict()

        if worlds[0].owl_drops:
            one_way_entrance_pools['OwlDrop'] = world.get_shufflable_entrances(type='OwlDrop')

        if worlds[0].spawn_positions:
            one_way_entrance_pools['Spawn'] = world.get_shufflable_entrances(type='Spawn')

        if worlds[0].warp_songs:
            one_way_entrance_pools['WarpSong'] = world.get_shufflable_entrances(type='WarpSong')

        if worlds[0].shuffle_dungeon_entrances:
            entrance_pools['Dungeon'] = world.get_shufflable_entrances(type='Dungeon', only_primary=True)
            # The fill algorithm will already make sure gohma is reachable, however it can end up putting
            # a forest escape via the hands of spirit on Deku leading to Deku on spirit in logic. This is
            # not really a closed forest anymore, so specifically remove Deku Tree from closed forest.
            if worlds[0].open_forest == 'closed':
                entrance_pools['Dungeon'].remove(world.get_entrance('Outside Deku Tree -> Deku Tree Lobby'))
            if worlds[0].decouple_entrances:
                entrance_pools['DungeonReverse'] = [entrance.reverse for entrance in entrance_pools['Dungeon']]

        if worlds[0].shuffle_interior_entrances:
            entrance_pools['Interior'] = world.get_shufflable_entrances(type='Interior', only_primary=True)
            if worlds[0].shuffle_special_interior_entrances:
                entrance_pools['Interior'] += world.get_shufflable_entrances(type='SpecialInterior', only_primary=True)
            if worlds[0].decouple_entrances:
                entrance_pools['InteriorReverse'] = [entrance.reverse for entrance in entrance_pools['Interior']]

        if worlds[0].shuffle_grotto_entrances:
            entrance_pools['GrottoGrave'] = world.get_shufflable_entrances(type='Grotto', only_primary=True)
            entrance_pools['GrottoGrave'] += world.get_shufflable_entrances(type='Grave', only_primary=True)
            if worlds[0].decouple_entrances:
                entrance_pools['GrottoGraveReverse'] = [entrance.reverse for entrance in entrance_pools['GrottoGrave']]

        if worlds[0].shuffle_overworld_entrances:
            exclude_overworld_reverse = worlds[0].mix_entrance_pools and not worlds[0].decouple_entrances
            entrance_pools['Overworld'] = world.get_shufflable_entrances(type='Overworld', only_primary=exclude_overworld_reverse)

        # Set shuffled entrances as such
        for entrance in list(chain.from_iterable(one_way_entrance_pools.values())) + list(chain.from_iterable(entrance_pools.values())):
            entrance.shuffled = True
            if entrance.reverse:
                entrance.reverse.shuffled = True

        # Combine all entrance pools into one when mixing entrance pools
        if worlds[0].mix_entrance_pools:
            entrance_pools = {'Mixed': list(chain.from_iterable(entrance_pools.values()))}

        # Build target entrance pools and set the assumption for entrances being reachable
        one_way_target_entrance_pools = {}
        for pool_type, entrance_pool in one_way_entrance_pools.items():
            # One way entrances are extra entrances that will be connected to entrance positions from a selection of entrance pools
            if pool_type == 'OwlDrop':
                valid_target_types = ('WarpSong', 'OwlDrop', 'Overworld', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types, exclude=['Prelude of Light Warp -> Temple of Time'])
                for target in one_way_target_entrance_pools[pool_type]:
                    target.set_rule(lambda state, age=None, **kwargs: age == 'child')
            elif pool_type == 'Spawn':
                valid_target_types = ('Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types)
            elif pool_type == 'WarpSong':
                valid_target_types = ('Spawn', 'WarpSong', 'OwlDrop', 'Overworld', 'Interior', 'SpecialInterior', 'Grotto', 'Grave', 'Extra')
                one_way_target_entrance_pools[pool_type] = build_one_way_targets(world, valid_target_types)
            # Ensure that when trying to place the last entrance of a one way pool, we don't assume the rest of the targets are reachable
            for target in one_way_target_entrance_pools[pool_type]:
                target.add_rule((lambda entrances=entrance_pool: (lambda state, **kwargs: any(entrance.connected_region == None for entrance in entrances)))())
        # Disconnect all one way entrances at this point (they need to be connected during all of the above process)
        for entrance in chain.from_iterable(one_way_entrance_pools.values()):
            entrance.disconnect()

        target_entrance_pools = {}
        for pool_type, entrance_pool in entrance_pools.items():
            target_entrance_pools[pool_type] = assume_entrance_pool(entrance_pool)

        # Set entrances defined in the distribution
        world.distribution.set_shuffled_entrances(worlds, dict(chain(one_way_entrance_pools.items(), entrance_pools.items())), dict(chain(one_way_target_entrance_pools.items(), target_entrance_pools.items())), locations_to_ensure_reachable, complete_itempool)

        # Shuffle all entrances among the pools to shuffle
        for pool_type, entrance_pool in one_way_entrance_pools.items():
            shuffle_entrance_pool(world, worlds, entrance_pool, one_way_target_entrance_pools[pool_type], locations_to_ensure_reachable, check_all=True)
            # Delete all targets that we just placed from other one way target pools so multiple one way entrances don't use the same target
            replaced_entrances = [entrance.replaces for entrance in entrance_pool]
            for remaining_target in chain.from_iterable(one_way_target_entrance_pools.values()):
                if remaining_target.replaces in replaced_entrances:
                    delete_target_entrance(remaining_target)
            # Delete all unused extra targets after placing a one way pool, since the unused targets won't ever be replaced
            for unused_target in one_way_target_entrance_pools[pool_type]:
                delete_target_entrance(unused_target)

        for pool_type, entrance_pool in entrance_pools.items():
            shuffle_entrance_pool(world, worlds, entrance_pool, target_entrance_pools[pool_type], locations_to_ensure_reachable)

    # Multiple checks after shuffling entrances to make sure everything went fine
    max_playthrough = Playthrough.max_explore([world.state for world in worlds], complete_itempool)

    # Check that all shuffled entrances are properly connected to a region
    for world in worlds:
        for entrance in world.get_shuffled_entrances():
            if entrance.connected_region == None:
                logging.getLogger('').error('%s was shuffled but still isn\'t connected to any region [World %d]', entrance, world.id)
            if entrance.replaces == None:
                logging.getLogger('').error('%s was shuffled but still doesn\'t replace any entrance [World %d]', entrance, world.id)
    if len(world.get_region('Root Exits').exits) > 8:
        for exit in world.get_region('Root Exits').exits:
            logging.getLogger('').error('Root Exit: %s, Connected Region: %s', exit, exit.connected_region)
        raise RuntimeError('Something went wrong, Root has too many entrances left after shuffling entrances [World %d]' % world.id)

    # Check for game beatability in all worlds
    if not max_playthrough.can_beat_game(False):
        raise EntranceShuffleError('Cannot beat game!')

    # Validate the worlds one last time to ensure all special conditions are still valid
    for world in worlds:
        try:
            validate_world(world, worlds, None, locations_to_ensure_reachable, complete_itempool)
        except EntranceShuffleError as error:
            raise EntranceShuffleError('Worlds are not valid after shuffling entrances, Reason: %s' % error)


# Shuffle all entrances within a provided pool
def shuffle_entrance_pool(world, worlds, entrance_pool, target_entrances, locations_to_ensure_reachable, check_all=False, retry_count=20):

    # Split entrances between those that have requirements (restrictive) and those that do not (soft). These are primarily age or time of day requirements.
    restrictive_entrances, soft_entrances = split_entrances_by_requirements(worlds, entrance_pool, target_entrances)

    while retry_count:
        retry_count -= 1
        rollbacks = []

        try:
            # Shuffle restrictive entrances first while more regions are available in order to heavily reduce the chances of the placement failing.
            shuffle_entrances(worlds, restrictive_entrances, target_entrances, rollbacks, locations_to_ensure_reachable)

            # Shuffle the rest of the entrances, we don't have to check for beatability/reachability of locations when placing those, unless specified otherwise
            if check_all:
                shuffle_entrances(worlds, soft_entrances, target_entrances, rollbacks, locations_to_ensure_reachable)
            else:
                shuffle_entrances(worlds, soft_entrances, target_entrances, rollbacks)

            # Fully validate the resulting world to ensure everything is still fine after shuffling this pool
            complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
            validate_world(world, worlds, None, locations_to_ensure_reachable, complete_itempool)

            # If all entrances could be connected without issues, log connections and continue
            for entrance, target in rollbacks:
                confirm_replacement(entrance, target)
            return

        except EntranceShuffleError as error:
            for entrance, target in rollbacks:
                restore_connections(entrance, target)
            logging.getLogger('').info('Failed to place all entrances in a pool for world %d. Will retry %d more times', entrance_pool[0].world.id, retry_count)
            logging.getLogger('').info('\t%s' % error)

    raise EntranceShuffleError('Entrance placement attempt count exceeded for world %d' % entrance_pool[0].world.id)


# Split entrances based on their requirements to figure out how each entrance should be handled when shuffling them
def split_entrances_by_requirements(worlds, entrances_to_split, assumed_entrances):

    # First, disconnect all root assumed entrances and save which regions they were originally connected to, so we can reconnect them later
    original_connected_regions = {}
    entrances_to_disconnect = set(assumed_entrances).union(entrance.reverse for entrance in assumed_entrances if entrance.reverse)
    for entrance in entrances_to_disconnect:
        if entrance.connected_region:
            original_connected_regions[entrance] = entrance.disconnect()

    # Generate the states with all assumed entrances disconnected
    # This ensures no assumed entrances corresponding to those we are shuffling are required in order for an entrance to be reachable as some age/tod
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]
    max_playthrough = Playthrough.max_explore([world.state for world in worlds], complete_itempool)

    restrictive_entrances = []
    soft_entrances = []

    for entrance in entrances_to_split:
        # Here, we find entrances that may be unreachable under certain conditions
        if not max_playthrough.spot_access(entrance, age='both', tod=TimeOfDay.ALL):
            restrictive_entrances.append(entrance)
            continue
        # If an entrance is reachable as both ages and all times of day with all the other entrances disconnected,
        # then it can always be made accessible in all situations by the Fill algorithm, no matter which combination of entrances we end up with.
        # Thus, those entrances aren't bound to any specific requirements and are very versatile during placement.
        soft_entrances.append(entrance)

    # Reconnect all disconnected entrances afterwards
    for entrance in entrances_to_disconnect:
        if entrance in original_connected_regions:
            entrance.connect(original_connected_regions[entrance])

    return restrictive_entrances, soft_entrances


# Shuffle entrances by placing them instead of entrances in the provided target entrances list
# While shuffling entrances, the algorithm will ensure worlds are still valid based on multiple criterias
def shuffle_entrances(worlds, entrances, target_entrances, rollbacks, locations_to_ensure_reachable=[]):

    # Retrieve all items in the itempool, all worlds included
    complete_itempool = [item for world in worlds for item in world.get_itempool_with_dungeon_items()]

    random.shuffle(entrances)

    # Place all entrances in the pool, validating worlds during every placement
    for entrance in entrances:
        if entrance.connected_region != None:
            continue
        random.shuffle(target_entrances)

        for target in target_entrances:
            if target.connected_region == None:
                continue

            try:
                check_entrances_compatibility(entrance, target)
                change_connections(entrance, target)
                validate_world(entrance.world, worlds, entrance, locations_to_ensure_reachable, complete_itempool)
                rollbacks.append((entrance, target))
                break
            except EntranceShuffleError as error:
                # If the entrance can't be placed there, log a debug message and change the connections back to what they were previously
                logging.getLogger('').debug('Failed to connect %s To %s (Reason: %s) [World %d]',
                                            entrance, entrance.connected_region or target.connected_region, error, entrance.world.id)
                if entrance.connected_region:
                    restore_connections(entrance, target)

        if entrance.connected_region == None:
            raise EntranceShuffleError('No more valid entrances to replace with %s in world %d' % (entrance, entrance.world.id))


# Check and validate that an entrance is compatible to replace a specific target
def check_entrances_compatibility(entrance, target):
    # An entrance shouldn't be connected to its own scene, so we fail in that situation
    if entrance.parent_region.get_scene() and entrance.parent_region.get_scene() == target.connected_region.get_scene():
        raise EntranceShuffleError('Self scene connections are forbidden')


# Validate the provided worlds' structures, raising an error if it's not valid based on our criterias
def validate_world(world, worlds, entrance_placed, locations_to_ensure_reachable, itempool):

    if not world.decouple_entrances:
        # Unless entrances are decoupled, we don't want the player to end up through certain entrances as the wrong age
        # This means we need to hard check that none of the relevant entrances are ever reachable as that age
        # This is mostly relevant when mixing entrance pools or shuffling special interiors (such as windmill or kak potion shop)
        # Warp Songs and Overworld Spawns can also end up inside certain indoors so those need to be handled as well
        CHILD_FORBIDDEN = ['Ganons Castle Fairy -> Castle Grounds', 'Carpenter Tent -> Gerudo Valley Far Side']
        ADULT_FORBIDDEN = ['Hyrule Castle Fairy -> Castle Grounds', 'Castle Storms Grotto -> Castle Grounds']

        for entrance in world.get_shufflable_entrances():
            if entrance.shuffled:
                if entrance.replaces:
                    if entrance.replaces.name in CHILD_FORBIDDEN and not entrance_unreachable_as(entrance, 'child', already_checked=[entrance.replaces.reverse]):
                        raise EntranceShuffleError('%s is replaced by an entrance with a potential child access' % entrance.replaces.name)
                    elif entrance.replaces.name in ADULT_FORBIDDEN and not entrance_unreachable_as(entrance, 'adult', already_checked=[entrance.replaces.reverse]):
                        raise EntranceShuffleError('%s is replaced by an entrance with a potential adult access' % entrance.replaces.name)
            else:
                if entrance.name in CHILD_FORBIDDEN and not entrance_unreachable_as(entrance, 'child', already_checked=[entrance.reverse]):
                    raise EntranceShuffleError('%s is potentially accessible as child' % entrance.name)
                elif entrance.name in ADULT_FORBIDDEN and not entrance_unreachable_as(entrance, 'adult', already_checked=[entrance.reverse]):
                    raise EntranceShuffleError('%s is potentially accessible as adult' % entrance.name)

    if locations_to_ensure_reachable:
        max_playthrough = Playthrough.max_explore([w.state for w in worlds], itempool)
        # If ALR is enabled, ensure all locations we want to keep reachable are indeed still reachable
        # Otherwise, just continue if the game is still beatable
        if not (world.check_beatable_only and max_playthrough.can_beat_game(False)):
            max_playthrough.visit_locations(locations_to_ensure_reachable)
            for location in locations_to_ensure_reachable:
                if not max_playthrough.visited(location):
                    raise EntranceShuffleError('%s is unreachable' % location.name)

    if (world.shuffle_special_interior_entrances or world.shuffle_overworld_entrances or world.spawn_positions) and \
       (entrance_placed == None or world.mix_entrance_pools or entrance_placed.type in ['SpecialInterior', 'Overworld', 'Spawn', 'WarpSong', 'OwlDrop']):
            # At least one valid starting region with all basic refills should be reachable without using any items at the beginning of the seed
            # Note this creates an empty State rather than reuse world.state (which already has starting items).
            no_items_playthrough = Playthrough([State(w) for w in worlds])

            valid_starting_regions = ['Kokiri Forest', 'Kakariko Village']
            if not any(region for region in valid_starting_regions if no_items_playthrough.can_reach(world.get_region(region))):
                raise EntranceShuffleError('Invalid starting area')

            # Check that a region where time passes is always reachable as both ages without having collected any items (except in closed forest)
            time_travel_playthrough = Playthrough.with_items([w.state for w in worlds], [ItemFactory('Time Travel', world=w) for w in worlds])

            if not (any(region for region in time_travel_playthrough.reachable_regions('child') if region.time_passes and region.world == world) and
                    any(region for region in time_travel_playthrough.reachable_regions('adult') if region.time_passes and region.world == world)):
                raise EntranceShuffleError('Time passing is not guaranteed as both ages')

            # The player should be able to get back to ToT after going through time, without having collected any items
            # This is important to ensure that the player never loses access to the pedestal after going through time
            if world.starting_age == 'child' and not time_travel_playthrough.can_reach(world.get_region('Temple of Time'), age='adult'):
                raise EntranceShuffleError('Path to Temple of Time as adult is not guaranteed')
            elif world.starting_age == 'adult' and not time_travel_playthrough.can_reach(world.get_region('Temple of Time'), age='child'):
                raise EntranceShuffleError('Path to Temple of Time as child is not guaranteed')

    if (world.shuffle_interior_entrances or world.shuffle_overworld_entrances) and \
       (entrance_placed == None or world.mix_entrance_pools or entrance_placed.type in ['Interior', 'SpecialInterior', 'Overworld', 'Spawn', 'WarpSong', 'OwlDrop']):
        # The Big Poe Shop should always be accessible as adult without the need to use any bottles
        # Since we can't guarantee that items in the pool won't be placed behind bottles, we guarantee the access without using any items
        # This is important to ensure that players can never lock their only bottles by filling them with Big Poes they can't sell
        no_items_time_travel_playthrough = Playthrough.with_items([State(w) for w in worlds], [ItemFactory('Time Travel', world=w) for w in worlds])

        if not no_items_time_travel_playthrough.can_reach(world.get_region('Castle Town Rupee Room'), age='adult'):
            raise EntranceShuffleError('Big Poe Shop access is not guaranteed as adult')

        if world.shuffle_cows:
            impas_front_entrance = get_entrance_replacing(world.get_region('Impas House'), 'Kakariko Village -> Impas House')
            impas_back_entrance = get_entrance_replacing(world.get_region('Impas House Back'), 'Kakariko Impa Ledge -> Impas House Back')
            check_same_hint_region(impas_front_entrance, impas_back_entrance)


# Returns whether or not we can affirm the entrance can never be accessed as the given age
def entrance_unreachable_as(entrance, age, already_checked=None):
    if already_checked == None:
        already_checked = []

    already_checked.append(entrance)

    # The following cases determine when we say an entrance is not safe to affirm unreachable as the given age
    if entrance.type in ('WarpSong', 'Overworld'):
        # Note that we consider all overworld entrances as potentially accessible as both ages, to be completely safe
        return False
    elif entrance.type == 'OwlDrop':
        return age == 'adult'
    elif entrance.name == 'Child Spawn -> Links House':
        return age == 'adult'
    elif entrance.name == 'Adult Spawn -> Temple of Time':
        return age == 'child'

    # Other entrances such as Interior, Dungeon or Grotto are fine unless they have a parent which is one of the above cases
    # Recursively check parent entrances to verify that they are also not reachable as the wrong age
    for parent_entrance in entrance.parent_region.entrances:
        if parent_entrance in already_checked: continue
        unreachable = entrance_unreachable_as(parent_entrance, age, already_checked)
        if not unreachable:
            return False

    return True


# Shorthand function to check and validate that two entrances are in the same hint region
def check_same_hint_region(first, second):
    if  first.parent_region.hint is not None and second.parent_region.hint is not None and \
        first.parent_region.hint != second.parent_region.hint:
        raise EntranceShuffleError('Entrances are not in the same hint region')


# Shorthand function to find an entrance with the requested name leading to a specific region
def get_entrance_replacing(region, entrance_name):
    try:
        return next(filter(lambda entrance: entrance.replaces and entrance.replaces.name == entrance_name, region.entrances))
    except StopIteration:
        return region.world.get_entrance(entrance_name)


# Change connections between an entrance and a target assumed entrance, in order to test the connections afterwards if necessary
def change_connections(entrance, target_entrance):
    entrance.connect(target_entrance.disconnect())
    entrance.replaces = target_entrance.replaces
    if entrance.reverse and not entrance.world.decouple_entrances:
        target_entrance.replaces.reverse.connect(entrance.reverse.assumed.disconnect())
        target_entrance.replaces.reverse.replaces = entrance.reverse


# Restore connections between an entrance and a target assumed entrance
def restore_connections(entrance, target_entrance):
    target_entrance.connect(entrance.disconnect())
    entrance.replaces = None
    if entrance.reverse and not entrance.world.decouple_entrances:
        entrance.reverse.assumed.connect(target_entrance.replaces.reverse.disconnect())
        target_entrance.replaces.reverse.replaces = None


# Confirm the replacement of a target entrance by a new entrance, logging the new connections and completely deleting the target entrances
def confirm_replacement(entrance, target_entrance):
    delete_target_entrance(target_entrance)
    logging.getLogger('').debug('Connected %s To %s [World %d]', entrance, entrance.connected_region, entrance.world.id)
    if entrance.reverse and not entrance.world.decouple_entrances:
        replaced_reverse = target_entrance.replaces.reverse
        delete_target_entrance(entrance.reverse.assumed)
        logging.getLogger('').debug('Connected %s To %s [World %d]', replaced_reverse, replaced_reverse.connected_region, replaced_reverse.world.id)


# Delete an assumed target entrance, by disconnecting it if needed and removing it from its parent region
def delete_target_entrance(target_entrance):
    if target_entrance.connected_region != None:
        target_entrance.disconnect()
    if target_entrance.parent_region != None:
        target_entrance.parent_region.exits.remove(target_entrance)
        target_entrance.parent_region = None
