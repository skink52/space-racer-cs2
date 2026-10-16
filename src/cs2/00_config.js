// ===================================================================================
// Space Racer for CS2 - CS2 side. Settings you may want to change are in CONFIG.
// ===================================================================================

const CONFIG = {
  // ---- race rules
  ARENA_LAYOUT: '2x32',          // '2x32': up to 2 arenas of 32 (33+ split evenly); '4x16': up to 4 arenas of 16; 'alternate': switch each round
  ARENA_MIN: 8,                  // with more than one arena, none has fewer than this
  ENGINE_HUM: true,              // engine sound on every human-driven car (pitch follows speed)
  MUSIC: true,                   // chiptune music for everyone: a lobby loop, a race loop and a results fanfare
  MIN_PLAYERS: 1,                // fewer than this on T/CT (bots count): no race, everyone waits in the lobby
  LAPS: 0,                       // 0 = each track's own lap count
  COUNTDOWN: 10,                 // seconds on the grid before the lights
  FINISH_WINDOW: 30,             // seconds the rest get after the winner crosses the line
  RACE_CAP: 300,                 // seconds: a race is cut off and ranked by distance after this
  RESULTS_HOLD: 6,               // seconds the results stay up before the arena is over
  TRACK_BLACKLIST: [],           // e.g. ["nullgap"] to never race it
  DEFAULT_CAR: 'hornet',

  // ---- the CS2 round result and kill credit
  TIEBREAK: true,                // equal top-8 counts: the side with the better single finish wins (false = draw)
  PODIUM: 3,                     // the top N of each arena survive; everyone else takes one CS2 death
  SHARES: [50, 30, 20],          // the losers' deaths are credited as kills to 1st / 2nd / 3rd in these percentages
  KO_CREDIT_TO_ATTACKER: true,   // a car wrecked by someone's attack is a kill for that player at once (left out of the shares)
  REAL_KILLS: true,              // CS2 kills through TakeDamage (killfeed, scoreboard, rank plugins)
  KILL_CASCADE_TICKS: 3,         // end-of-race deaths go out one every N ticks so the killfeed rolls
  ADD_SCORE: false,              // only when REAL_KILLS is off: AddScore(+1) per credited kill

  // ---- AFK
  AFK_WARN: 20, AFK_KICK: 30,    // seconds without input during a race

  // ---- bots
  CS2_BOTS_PLAY: true,
  BOT_SKILL: 0.5,

  // ---- server settings the map applies (APPLY_CVARS false leaves the server config alone)
  APPLY_CVARS: true,
  CVARS_ALWAYS: [
    'mp_respawn_immunitytime 0', 'mp_death_drop_gun 0', 'mp_buy_anywhere 0', 'mp_buytime 0', 'sv_disable_radar 1',
    'mp_respawn_on_death_t 1', 'mp_respawn_on_death_ct 1', 'mp_teammates_are_enemies 1',
  ],
  ROUND_SLACK: 15,               // the CS2 round clock runs this much longer than the race can, so the script ends it

  // ---- camera
  // chase camera presets (each player picks with !cam): back / up from the car, pitch down, extra pull-back at full speed.
  // 'high' (the default) sits up and back so the track ahead is visible a long way off.
  CAMERAS: {
    high: { back: 290, up: 165, pitch: 15, speedBack: 60 },
    far:  { back: 420, up: 260, pitch: 22, speedBack: 80 },
    near: { back: 230, up: 100, pitch: 9, speedBack: 30 },
  },
  CAM_DEFAULT: 'high',
  CAM_TURN: 6.0,                 // how quickly the camera swings round behind the car
  CAM_LOOKAHEAD: 0.35,           // 0..1: how much the camera turns into the bend ahead (shows more of the upcoming track)
  CAM_ROLL: 8,                   // max degrees of lean in corners
  CAM_SHAKE: 1.0,                // camera shake on hits / landings / wrecks (0 = off, 2 = double)
  CAM_BANK: 0.6,                 // how much of a banked bend's lean the camera copies
  CAM_TUBE_UP: 150, CAM_TUBE_BACK: 300,   // camera height / distance limits inside tubes
  HIDE_OWN_BODY: true,

  // ---- rendering
  MAX_EFFECT_PROPS: 40,          // per arena
  MAX_SOUNDS_PER_TICK: 24,
  SPAWN_BUDGET: 24,              // new props per server tick at most
  HUD_BUDGET: 900,               // HUD changes per server tick at most (pixel text sends one per changed letter)
  STANDINGS_PERIOD: 0.5,         // seconds between standings refreshes

  // ---- input
  CHAT_COMMANDS: true,
  HELP_SECONDS: 10,
  SAY_GAP: 1.0,

  // ---- entity names in the map
  HUD: 'spr_hud',
  PROP_TEMPLATE: 'spr_tpl_prop',
  BOOTH: 'spr_booth',
  SOUND_PREFIX: 'spr_snd_',
  MAP_PARAMS: 'spr_map_params',

  DEBUG: false,
};

const VERSION = '0.3.0';
