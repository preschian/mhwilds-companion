-- GunlanceShells: +N shells over each Gunlance's native capacity.
--
-- How it works: every Gunlance keeps its ammo in app.cAmmo (_Ammo on the
-- Gunlance handler). The game recomputes the native capacity from the
-- equipped weapon (plus skills) in setupLimitAmmo. This mod post-hooks:
--   setupLimitAmmo -> raise the fresh native limit by cfg.bonus
--   reloadShell    -> re-apply after silent resets, live config changes,
--                     or when the mod is disabled mid-session
-- Per-weapon differences are preserved: the bonus is added on top of
-- whatever base the current weapon (and skills) provide.

local MOD = "GunlanceShells"
local VERSION = "1.0.0"

local MIN_BONUS, MAX_BONUS, DEFAULT_BONUS = 1, 50, 10

local cfg = { enabled = true, bonus = DEFAULT_BONUS }

-- [ammo address] = { base = native limit, applied = bonus in effect }
local tracked = {}
local fallback_entry = nil -- used when get_address is unavailable
local status = "idle"
local applications = 0

local function modlog(msg)
  local s = "[" .. MOD .. "] " .. tostring(msg)
  if type(log) == "table" and type(log.info) == "function" then log.info(s)
  elseif type(log) == "function" then log(s)
  else print(s) end
end

local function to_int(v)
  if v == nil then return nil end
  if type(v) == "number" then return math.floor(v) end
  local ok, n = pcall(sdk.to_int64, v)
  if ok and n ~= nil then return tonumber(n) end
  return tonumber(tostring(v))
end

local function get_ammo(handling)
  if handling == nil then return nil end
  local ammo = nil
  pcall(function() ammo = handling:get_field("_Ammo") end)
  return ammo
end

local function read_limits(ammo)
  if ammo == nil then return nil, nil end
  local limit, loaded = nil, nil
  pcall(function() limit = to_int(ammo:call("get_LimitAmmo")) end)
  pcall(function() loaded = to_int(ammo:call("get_LoadedAmmo")) end)
  return limit, loaded
end

local function write_limits(ammo, limit, loaded)
  if ammo == nil or limit == nil then return false end
  local ok = pcall(function() ammo:call("setLimitAmmo", limit) end)
  if not ok then return false end
  if loaded ~= nil then
    pcall(function() ammo:call("setLoadedAmmo", loaded) end)
  end
  return true
end

local function track_key(ammo)
  local ok, addr = pcall(function() return ammo:get_address() end)
  if ok and addr ~= nil then return addr end
  return nil
end

local function get_entry(ammo)
  local key = track_key(ammo)
  if key == nil then return fallback_entry, nil end
  return tracked[key], key
end

local function set_entry(ammo, key, entry)
  if key == nil then fallback_entry = entry
  else tracked[key] = entry end
end

local function note_applied(base, total, reason)
  applications = applications + 1
  status = string.format("base %d + %d = %d shells (%s)", base, total - base, total, reason)
  modlog(status)
end

-- Post-setupLimitAmmo: the game just wrote the native limit.
local function on_setup(handling)
  local ammo = get_ammo(handling)
  if ammo == nil then return end
  local limit, loaded = read_limits(ammo)
  if limit == nil then return end
  loaded = loaded or 0
  local entry, key = get_entry(ammo)
  -- If the game left a previous bonus in place (no recompute), reuse the
  -- known base so repeated setups never stack the bonus.
  local base = limit
  if entry and limit == entry.base + entry.applied then base = entry.base end
  if not cfg.enabled or cfg.bonus < 1 then
    set_entry(ammo, key, { base = base, applied = 0 })
    status = string.format("disabled: native %d shells", base)
    if limit ~= base then write_limits(ammo, base, math.min(loaded, base)) end
    return
  end
  local bonus = math.floor(cfg.bonus)
  local total = base + bonus
  set_entry(ammo, key, { base = base, applied = bonus })
  if limit ~= total then
    -- Preserve the current deficit (fired shells stay fired).
    local deficit = math.max(0, limit - loaded)
    write_limits(ammo, total, math.max(0, total - deficit))
    note_applied(base, total, "setup")
  else
    status = string.format("base %d + %d = %d shells (setup, already applied)", base, bonus, total)
  end
end

-- Post-reloadShell: enforce the bonus across silent resets and live changes.
local function on_reload(handling)
  local ammo = get_ammo(handling)
  if ammo == nil then return end
  local limit, loaded = read_limits(ammo)
  if limit == nil then return end
  loaded = loaded or 0
  local entry, key = get_entry(ammo)
  if entry == nil then return end -- never adopt an unknown limit as base
  if not cfg.enabled or cfg.bonus < 1 then
    if entry.applied > 0 and limit == entry.base + entry.applied then
      write_limits(ammo, entry.base, math.min(loaded, entry.base))
      entry.applied = 0
      status = string.format("disabled: restored %d shells", entry.base)
      modlog(status)
    elseif limit ~= entry.base then
      entry.base = limit -- native base moved while disabled; resync
    end
    return
  end
  local bonus = math.floor(cfg.bonus)
  if limit == entry.base + entry.applied and bonus == entry.applied then
    return -- steady state
  end
  local base = entry.base
  if limit ~= entry.base and limit ~= entry.base + entry.applied then
    base = limit -- native base changed outside setup (e.g. skill path)
  end
  local total = base + bonus
  local deficit = math.max(0, limit - loaded)
  if write_limits(ammo, total, math.max(0, total - deficit)) then
    set_entry(ammo, key, { base = base, applied = bonus })
    note_applied(base, total, "reload")
  end
end

local t = sdk.find_type_definition("app.cHunterWp07Handling")
if not t then
  modlog("ERROR: app.cHunterWp07Handling missing")
  return
end
local m_setup = t:get_method("setupLimitAmmo")
local m_reload = t:get_method("reloadShell")
if not m_setup or not m_reload then
  modlog("ERROR: method missing")
  return
end

sdk.hook(m_setup, function(args)
  thread.get_hook_storage()["this"] = sdk.to_managed_object(args[2])
end, function(retval)
  pcall(function() on_setup(thread.get_hook_storage()["this"]) end)
  return retval
end)

sdk.hook(m_reload, function(args)
  thread.get_hook_storage()["this"] = sdk.to_managed_object(args[2])
end, function(retval)
  pcall(function() on_reload(thread.get_hook_storage()["this"]) end)
  return retval
end)

re.on_draw_ui(function()
  if not imgui.tree_node(MOD .. " v" .. VERSION) then return end
  pcall(function()
    imgui.text(tostring(status))
    imgui.text("applications: " .. tostring(applications))
    local _, enabled = imgui.checkbox("Enabled", cfg.enabled)
    cfg.enabled = enabled
    if type(imgui.slider_int) == "function" then
      local _, bonus = imgui.slider_int("Bonus shells", cfg.bonus, MIN_BONUS, MAX_BONUS)
      cfg.bonus = math.max(MIN_BONUS, math.min(MAX_BONUS, math.floor(bonus)))
    else
      imgui.text("Bonus shells: " .. tostring(cfg.bonus))
      if imgui.button("Bonus -1") then cfg.bonus = math.max(MIN_BONUS, cfg.bonus - 1) end
      if imgui.button("Bonus +1") then cfg.bonus = math.min(MAX_BONUS, cfg.bonus + 1) end
    end
    imgui.text("Bonus applies on Gunlance setup;")
    imgui.text("changes apply on the next reload.")
  end)
  imgui.tree_pop()
end)

modlog(VERSION .. " loaded")
