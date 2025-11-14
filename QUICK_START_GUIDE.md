# 🚀 SCUM Server Quick Start Guide

## Get Your Custom Server Running in 5 Minutes!

---

## Step 1: Choose Your Server Type

Pick from 8 pre-configured presets:

| Type | Best For | Difficulty | Loot | Action |
|------|----------|------------|------|--------|
| **PvE Casual** | New players, learning | ⭐ Easy | 🎁🎁 High | ⚔️ Low |
| **PvP Hardcore** | Veterans, challenge | ⭐⭐⭐⭐⭐ Extreme | 🎁 Scarce | ⚔️⚔️⚔️⚔️⚔️ Very High |
| **RP Realism** | Roleplay, immersion | ⭐⭐⭐ Medium | 🎁 Normal | ⚔️⚔️ Medium |
| **High Action** | Fast combat, loot | ⭐⭐ Easy-Medium | 🎁🎁🎁 Very High | ⚔️⚔️⚔️⚔️ High |
| **Performance** | Low-end hardware | ⭐⭐ Medium | 🎁 Normal | ⚔️⚔️ Medium |
| **Balanced** | Standard SCUM | ⭐⭐⭐ Medium | 🎁 Normal | ⚔️⚔️⚔️ Medium |
| **Survival Expert** | PvE challenge | ⭐⭐⭐⭐ Hard | 🎁 Low | ⚔️⚔️⚔️ High |
| **Build & Creative** | Building, creativity | ⭐ Very Easy | 🎁🎁🎁 High | ⚔️ Very Low |

---

## Step 2: Apply Your Preset

### Option A: Using the Manager GUI
1. Open **SCUM Server Manager Pro**
2. Click **"Auto Detect"** button
3. Go to **Config Editor** tab
4. Manually copy settings from `config_presets.json`
5. Click **"Save Config Files"**

### Option B: Manual Configuration
1. Navigate to your config folder:
   ```
   SCUM_Server/SCUM/Saved/Config/WindowsServer/
   ```
2. Open `config_presets.json`
3. Find your chosen preset
4. Copy each setting to the corresponding INI file
5. Save all files

---

## Step 3: Essential Settings to Change

### 🔒 Security (REQUIRED!)
Open `ServerSettings.ini`:
```ini
ServerName=YOUR SERVER NAME HERE
ServerPassword=             # Leave empty for public
ServerAdminPassword=CHANGE_THIS_PASSWORD_NOW
RCON_Password=CHANGE_THIS_TOO
ServerDescription=YOUR SERVER DESCRIPTION
```

### 🌍 Region & Visibility
```ini
ServerRegion=US             # US, EU, AS, OCE, SA, AF
ServerLanguage=EN           # EN, ES, FR, DE, RU, etc.
ServerListed=true           # Show in browser
MaxPlayers=64               # Your player limit
```

---

## Step 4: Fine-Tune Your Experience

### 🎮 Common Tweaks

#### Make It Easier
In `Game.ini`:
```ini
LootSpawnMultiplier=2.0     # Double the loot
PlayerDamageMultiplier=0.7  # Take 30% less damage
MetabolismRateMultiplier=0.5 # Hunger/thirst slower
RespawnTime=30.0            # Fast respawn
```

#### Make It Harder
In `Game.ini`:
```ini
LootSpawnMultiplier=0.5     # Half the loot
PlayerDamageMultiplier=1.5  # Take 50% more damage
AIMaxCount=100              # More zombies
AISpawnMultiplier=1.5       # 50% more zombie spawns
```

#### More Action
In `Game.ini`:
```ini
LootSpawnMultiplier=3.0     # Triple loot
AIMaxCount=75               # More zombies
EnableAIHordes=true         # Enable hordes
AirdropFrequency=1800.0     # Airdrops every 30 min
SkillGainMultiplier=2.0     # Level up faster
```

#### Better Performance
In `Game.ini`:
```ini
AIMaxCount=25               # Fewer zombies
SimulationDistance=5000.0   # Shorter range
MaxTickRate=20.0            # Lower tick rate
```

In `Scalability.ini`:
```ini
sg.ShadowQuality=0          # No shadows
sg.EffectsQuality=0         # Low effects
sg.ViewDistanceQuality=1    # Shorter view
```

---

## Step 5: Launch Your Server

### Using the Manager
1. Go to **Server Control** tab
2. Click **"Start Server"**
3. Monitor the **Output Log**
4. Wait for "Server Ready" message

### Manual Launch
1. Navigate to your SCUM server folder
2. Run `SCUMServer.exe`
3. Wait for initialization
4. Check ports are open (7777, 7778)

---

## 🔧 Quick Reference: Popular Settings

### Day/Night Speed
```ini
[Game.ini]
TimeAcceleration=4.0        # 1.0=real-time, 10.0=very fast
TimeAccelerationNightMultiplier=8.0  # Night time speed
```

### Loot Amounts
```ini
[Game.ini]
LootSpawnMultiplier=1.0     # 0.5=half, 2.0=double
WeaponSpawnMultiplier=1.0   # Weapon-specific
AmmoSpawnMultiplier=1.0     # Ammo-specific
```

### Zombie Settings
```ini
[Game.ini]
AIMaxCount=50               # Max zombies at once
AISpawnMultiplier=1.0       # Spawn frequency
AIHealthMultiplier=1.0      # Zombie HP
EnableAIHordes=true         # Horde events
HordeSize=15                # Zombies per horde
```

### Survival Rates
```ini
[Game.ini]
HungerRateMultiplier=1.0    # 0.5=slower, 2.0=faster
ThirstRateMultiplier=1.0    # Thirst speed
MetabolismRateMultiplier=1.0 # Overall metabolism
```

### Vehicle Settings
```ini
[Game.ini]
VehicleSpawnMultiplier=1.0  # Vehicle availability
VehicleFuelConsumptionMultiplier=1.0  # Fuel usage
MaxVehiclesPerPlayer=3      # Ownership limit
```

### Base Building
```ini
[Game.ini]
EnableBaseBuilding=true     # Allow construction
MaxBasesPerPlayer=3         # Base limit
EnableBaseRaiding=true      # Raiding allowed
RaidWindowStart=18.0        # Raid hours begin (6 PM)
RaidWindowEnd=6.0           # Raid hours end (6 AM)
```

---

## 🎯 Server Types Detailed

### 🟢 PvE Casual
**"Easy mode for beginners"**
- 2x loot spawns
- 50% less damage taken
- 50% slower hunger/thirst
- 30-second respawn
- Safe zones enabled
- No PvP

**Best for:** New players, friends, learning the game

### 🔴 PvP Hardcore
**"Brutal survival challenge"**
- 0.5x loot spawns (half)
- 2x damage taken
- 2x faster metabolism
- 5-minute death penalty
- 100 players max
- No safe zones
- Large zombie hordes

**Best for:** Experienced players, competitive PvP

### 🎭 RP Realism
**"Immersive roleplay experience"**
- Real-time day/night
- Full metabolism (hunger, thirst, vitamins, diseases, bladder)
- Faction system with wars
- Player trading & economy
- Raid windows (8 PM - 11 PM only)
- Realistic crafting times

**Best for:** Roleplay communities, immersion seekers

### ⚡ High Action
**"Constant combat & loot"**
- 3x loot spawns
- 2.5x weapon spawns
- Airdrops every 30 minutes
- Frequent events
- 2x XP & skills
- Fast respawn

**Best for:** Action lovers, casual PvP, fast-paced gameplay

### ⚙️ Performance Optimized
**"For low-end hardware"**
- Reduced AI count
- Lower simulation distance
- Optimized graphics
- Lower tick rate
- Compressed network data

**Best for:** Budget servers, high player counts on limited hardware

### ⚖️ Balanced Default
**"Standard SCUM experience"**
- All multipliers at 1.0x
- Normal day/night speed
- Standard loot
- Balanced difficulty

**Best for:** First-time server owners, standard gameplay

### 🏔️ Survival Expert
**"Tough PvE challenge"**
- 0.7x loot (30% less)
- Harsh weather effects
- Disease system active
- No PvP (focus on survival)
- Aggressive wildlife
- Large predator spawns

**Best for:** Solo/co-op survival challenge, PvE veterans

### 🏗️ Build & Creative
**"Focus on building & creativity"**
- 3x resource gathering
- Minimal enemy threats
- 70% faster crafting
- 10 bases per player
- No base raiding
- Reduced metabolism

**Best for:** Builders, creative mode, base showcases

---

## 📊 Performance Tips

### If Your Server Lags:
1. Lower `AIMaxCount` (try 25-30)
2. Reduce `SimulationDistance` (try 5000)
3. Lower `MaxTickRate` (try 20)
4. Reduce `MaxPlayers` (try 50)
5. Set `sg.ShadowQuality=0` in Scalability.ini
6. Disable `EnableDynamicWeather`

### For Smooth 100-Player Servers:
1. Use dedicated hardware (16GB+ RAM)
2. Set `TickRate=30` (no higher)
3. Set `AIMaxCount=30` (not 100)
4. Enable `UseCompression=true`
5. Set `SimulationDistance=7500`
6. Monitor CPU usage

---

## 🔍 Troubleshooting

### Server Won't Start
- Check config file syntax (no typos)
- Verify ports 7777, 7778 are open
- Check admin password is set
- Review server logs

### No Players Can Join
- Open firewall ports 7777, 7778
- Set `ServerListed=true`
- Check `MaxPlayers` not set to 0
- Verify `ServerPasswordRequired` matches actual password

### Low Performance
- Follow performance tips above
- Lower AI count
- Reduce player limit
- Check server hardware specs

### Settings Not Working
- Did you save the INI file?
- Did you restart the server?
- Check for typos in setting names
- Verify value ranges (e.g., 1.0 not "1.0x")

---

## 📚 Full Documentation

For complete details on all 365+ settings:
- Read **SCUM_CONFIG_GUIDE.md** (comprehensive reference)
- Check **COMPLETE_CONTROL_SUMMARY.md** (feature overview)
- View **config_presets.json** (preset details)

---

## 🎉 You're Ready!

1. ✅ Choose your server type
2. ✅ Apply the preset
3. ✅ Change security settings
4. ✅ Fine-tune experience
5. ✅ Launch and play!

**Have fun and happy server hosting! 🎮**

---

## 💡 Pro Tips

- **Always backup** before making changes
- **Test changes** on empty server first
- **Start with a preset**, then customize
- **Monitor performance** after changes
- **Join SCUM Discord** for community help
- **Update regularly** to latest SCUM version
- **Read the full guide** for advanced features

---

**Need More Help?**
- Full documentation: `SCUM_CONFIG_GUIDE.md`
- All settings explained: 365+ parameters documented
- Community: SCUM Official Discord
- Steam: SCUM Community Hub

*Made with ❤️ by SCUM Server Manager Pro*
