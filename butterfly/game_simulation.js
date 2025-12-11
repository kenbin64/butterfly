const fs = require('fs');
const yaml = require('js-yaml');
const sqlite3 = require('sqlite3');
const { performance } = require('perf_hooks');
const path = require('path');
const crypto = require('crypto');
const myapp = require('./myapp.js'); // Import the core framework
const PostgresStorageAdapter = require('./postgres_storage_adapter.js');

/**
 * A dedicated storage adapter for the game simulation.
 */
class GameStorage {
  constructor(config) {
    this.db = new sqlite3.Database(config.path, (err) => {
      if (err) {
        console.error(`[FATAL] Could not connect to database at ${config.path}`, err);
        process.exit(1);
      }
    });
  }

  async init() {
    await this._run(`
      CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL, -- 'player' or 'npc'
        name TEXT NOT NULL,
        hp INTEGER NOT NULL,
        max_hp INTEGER NOT NULL,
        attack_power INTEGER NOT NULL,
        position_x INTEGER NOT NULL,
        position_y INTEGER NOT NULL
      )
    `);
    await this._run(`
      CREATE TABLE IF NOT EXISTS game_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        turn INTEGER NOT NULL,
        actor_id TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        duration_ms REAL NOT NULL
      )
    `);
  }

  _run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function (err) { err ? reject(err) : resolve(this); });
    });
  }

  _get(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => { err ? reject(err) : resolve(row); });
    });
  }

  _all(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => { err ? reject(err) : resolve(rows); });
    });
  }

  async getCharacter(id) { return this._get('SELECT * FROM characters WHERE id = ?', [id]); }
  async getAllCharacters() { return this._all('SELECT * FROM characters'); }
  async updateCharacter(character) {
    const sql = `UPDATE characters SET hp = ?, position_x = ?, position_y = ? WHERE id = ?`;
    return this._run(sql, [character.hp, character.position_x, character.position_y, character.id]);
  }
  async logGameAction({ turn, actor_id, action, details, duration_ms }) {
    const sql = `INSERT INTO game_logs (timestamp, turn, actor_id, action, details, duration_ms) VALUES (?, ?, ?, ?, ?, ?)`;
    return this._run(sql, [new Date().toISOString(), turn, actor_id, action, details, duration_ms]);
  }
  async seedCharacters(characters) {
    const sql = `INSERT OR IGNORE INTO characters (id, type, name, hp, max_hp, attack_power, position_x, position_y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
    for (const char of characters) {
      await this._run(sql, [char.id, char.type, char.name, char.hp, char.max_hp, char.attack_power, char.position_x, char.position_y]);
    }
  }
  async close() { return new Promise((resolve, reject) => this.db.close((err) => (err ? reject(err) : resolve()))); }
}

/**
 * A simulated AI player that makes decisions for a character.
 * In a real implementation, this class would make API calls to an LLM
 * like Gemini to get strategic advice.
 */
class AIPlayer {
  constructor() {
    // In a real scenario, you might initialize an API client here.
  }

  /**
   * Chooses the next action for a character based on the game state.
   * @param {object} actor - The character controlled by the AI.
   * @param {object[]} allCharacters - The list of all characters on the board.
   * @returns {{action: string, target: object}} The chosen action and target.
   */
  chooseAction(actor, allCharacters) {
    // This simulates the core logic of an AI player.
    // 1. Identify threats (living NPCs).
    const threats = allCharacters.filter(c => c.type === 'npc' && c.hp > 0);
    if (threats.length === 0) {
      return { action: 'victory', target: null };
    }

    // 2. Prioritize the closest threat.
    const closestThreat = threats.sort((a, b) => this._distance(actor, a) - this._distance(actor, b))[0];

    // 3. Decide whether to attack or move.
    if (this._distance(actor, closestThreat) <= 1) {
      return { action: 'attack', target: closestThreat };
    }
    return { action: 'move', target: closestThreat };
  }

  _distance(charA, charB) { return Math.abs(charA.position_x - charB.position_x) + Math.abs(charA.position_y - charB.position_y); }
}

/**
 * Manages the state and logic of the RPG simulation.
 */
class GameEngine {
  constructor(storageAdapter) {
    this.storage = storageAdapter;
    this.turn = 0;
    this.playerAI = new AIPlayer(); // The engine now uses an AI for the player.
  }

  async initialize() {
    const characters = await this.storage.getAllCharacters();
    if (characters.length === 0) {
      console.log('No characters found. Seeding database with initial data...');
      await this.storage.seedCharacters([
        { id: 'player-1', type: 'player', name: 'Arion', hp: 100, max_hp: 100, attack_power: 15, position_x: 2, position_y: 3 },
        { id: 'npc-1', type: 'npc', name: 'Goblin', hp: 30, max_hp: 30, attack_power: 8, position_x: 5, position_y: 5 },
        { id: 'npc-2', type: 'npc', name: 'Orc', hp: 50, max_hp: 50, attack_power: 12, position_x: 8, position_y: 7 },
      ]);
    }
  }

  async runSimulation(turns = 5) {
    console.log(`Running game simulation for ${turns} turns...`);
    for (let i = 0; i < turns; i++) {
      this.turn++;
      const allCharacters = await this.storage.getAllCharacters();
      const player = await this.storage.getCharacter('player-1');
      const npcs = allCharacters.filter(c => c.type === 'npc' && c.hp > 0);

      if (player.hp <= 0) { await this._logAction(player, 'Defeated', 'Player has been defeated.'); break; }
      if (npcs.length === 0) { await this._logAction(player, 'Victory', 'All enemies defeated.'); break; }

      // --- Player's Turn (AI Controlled) ---
      const playerAction = this.playerAI.chooseAction(player, allCharacters);
      if (playerAction.action === 'move') {
        await this._moveTowards(player, playerAction.target);
      } else if (playerAction.action === 'attack') {
        await this._attack(player, playerAction.target);
      }

      // --- NPCs' Turn (Simple Logic) ---
      for (const npc of (await this.storage.getAllCharacters()).filter(c => c.type === 'npc' && c.hp > 0)) {
        const currentNpcState = await this.storage.getCharacter(npc.id);
        if (currentNpcState.hp > 0) {
          await this._moveTowards(currentNpcState, player);
          if (this._distance(currentNpcState, player) <= 1) { await this._attack(currentNpcState, player); }
        }
      }
    }
    console.log('Simulation complete.');
  }

  _distance(charA, charB) { return Math.abs(charA.position_x - charB.position_x) + Math.abs(charA.position_y - charB.position_y); }
  async _moveTowards(actor, target) {
    if (actor.position_x < target.position_x) actor.position_x++; else if (actor.position_x > target.position_x) actor.position_x--;
    if (actor.position_y < target.position_y) actor.position_y++; else if (actor.position_y > target.position_y) actor.position_y--;
    await this._logAction(actor, 'Move', `Moved to (${actor.position_x}, ${actor.position_y})`);
    await this.storage.updateCharacter(actor);
  }
  async _attack(attacker, defender) {
    const damage = Math.floor(attacker.attack_power * (0.8 + Math.random() * 0.4));
    defender.hp = Math.max(0, defender.hp - damage);
    await this._logAction(attacker, 'Attack', `Dealt ${damage} damage to ${defender.name}. ${defender.name} HP is now ${defender.hp}.`);
    await this.storage.updateCharacter(defender);
  }
  async _logAction(actor, action, details) {
    const startTime = performance.now();
    await this.storage.logGameAction({
      turn: this.turn, actor_id: actor.id, action: action, details: details, duration_ms: performance.now() - startTime,
    });
  }
}

async function main() {
  // --- 1. Secure Bootstrap (The application now bootstraps itself using the paradigm) ---
  const configPath = process.env.APP_CONFIG_PATH;
  if (!configPath) {
    console.error('[FATAL] APP_CONFIG_PATH environment variable not set. Cannot bootstrap system.');
    process.exit(1);
  }

  const publicKeyPath = process.env.APP_PUBLIC_KEY_PATH;
  if (!publicKeyPath) {
    console.error('[FATAL] APP_PUBLIC_KEY_PATH environment variable not set. Cannot verify config integrity.');
    process.exit(1);
  }

  let config;
  try {
    const configContent = fs.readFileSync(configPath, 'utf8');
    const signature = fs.readFileSync(configPath + '.sig');
    const publicKey = fs.readFileSync(publicKeyPath, 'utf8');
    const isVerified = crypto.verify(null, configContent, publicKey, signature);
    if (!isVerified) throw new Error('Configuration file signature is invalid!');
    config = yaml.load(configContent);
  } catch (err) {
    console.error(`[FATAL] Could not load or verify configuration: ${err.message}`);
    process.exit(1);
  }

  // --- 2. Initialize Internal Services using the Paradigm ---
  let storageAdapter;
  if (config.storage.type === 'sqlite') {
    // The application instantiates its own storage adapter using the library component.
    storageAdapter = new myapp.SecureResourceLocator.SqliteStorageAdapter(config.storage.sqlite);
  } else if (config.storage.type === 'postgres') {
    storageAdapter = new PostgresStorageAdapter(config.storage.postgres);
  } else {
    throw new Error(`Unsupported storage type: ${config.storage.type}`);
  }

  try {
    await storageAdapter.init();

    // The GameStorage class now uses the same adapter as the core services.
    const gameStorage = new GameStorage(config.storage.sqlite);
    // The game simulation initializes its own tables.
    await gameStorage.init();

    // --- 3. Run the Game Simulation ---
    const args = process.argv.slice(2);
    let turns = 5; // Default number of turns

    if (args.length > 0) {
      if (args[0] === '--help' || args[0] === '-h') {
        console.log('Usage: node game_simulation.js [number_of_turns]');
        console.log('  number_of_turns: A positive integer specifying how many turns to simulate. Defaults to 5.');
        return;
      }
      const parsedTurns = parseInt(args[0], 10);
      if (isNaN(parsedTurns) || parsedTurns <= 0) {
        console.error(`Error: Invalid argument. Please provide a positive integer for the number of turns.`);
        process.exit(1);
      }
      turns = parsedTurns;
    }

    const gameEngine = new GameEngine(gameStorage);
    await gameEngine.initialize();
    await gameEngine.runSimulation(turns);

  } finally {
    // Close the shared storage connection.
    if (gameStorage) {
      await gameStorage.close();
    }
    // The main storage adapter is no longer used directly in main, so we don't close it here.
    if (storageAdapter) {
      await storageAdapter.close();
    }
  }
}

main();