// ===================================================================================
// Space Racer for CS2 - CS2 side. Settings you may want to change are in CONFIG.
// ===================================================================================

const CONFIG = {
  // ---- race rules
  ARENA_MAX: 32, MAX_ARENAS: 2,  // 1-32 players race together; 33-64 are split evenly into two arenas
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
  CAM_BACK: 250, CAM_UP: 105, CAM_PITCH: 11, CAM_TURN: 7.0,   // chase camera: behind / above the car, pitch down, yaw follow speed
  CAM_ROLL: 10,                  // max degrees of lean in corners
  HIDE_OWN_BODY: true,

  // ---- rendering
  MAX_EFFECT_PROPS: 40,          // per arena
  MAX_SOUNDS_PER_TICK: 24,
  SPAWN_BUDGET: 24,              // new props per server tick at most
  HUD_BUDGET: 700,               // HUD changes per server tick at most
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

const VERSION = '0.1.0';
