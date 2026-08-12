-- StartupAutoJoin
-- Automatically advances to save slot 1 and the recommended lobby using the
-- game's own UI input controllers. No fixed delays or simulated key presses.

local MOD = "StartupAutoJoin"
local VERSION = "0.1.6"
local LOG_FILE = "startup_autojoin_v" .. VERSION .. ".txt"

local cfg = {
  enabled = true,
  skip_logo_movie = true,
  skip_autosave_notice = true,
  save_index = 0,
}

local title_menu_flow = nil
local title_menu_object = nil
local pending = {}
local completed = {}
local logo_movie = nil
local logo_flow_done = {}
local press_any_key = nil
local recommended_lobby_action = nil
local recommended_lobby_attempts = 0
local recommended_lobby_retry_frame = 0
local update_frame = 0
local runtime_active = true

local function log_line(message)
  local text = "[" .. MOD .. "] " .. tostring(message)
  if type(log) == "table" and type(log.info) == "function" then log.info(text) end
  pcall(function()
    local file = io.open(LOG_FILE, "a")
    if not file then return end
    file:write(os.date("%H:%M:%S ") .. tostring(message) .. "\n")
    file:close()
  end)
end

local function as_int(value)
  if value == nil then return nil end
  if type(value) == "number" then return math.floor(value) end
  local ok, number = pcall(sdk.to_int64, value)
  if ok and number ~= nil then return tonumber(number) end
  local ok_value, raw = pcall(function() return value:get_value() end)
  return ok_value and tonumber(raw) or nil
end

local function object_key(object, action)
  return tostring(object) .. ":" .. action
end

local function queue_input(object, field_name, index, action, callback_name)
  if not cfg.enabled or not object then return end
  if completed[action] then return end
  local key = object_key(object, action)
  if completed[key] then return end
  pending[key] = {
    object = object,
    field_name = field_name,
    index = index,
    action = action,
    callback_name = callback_name,
    attempts = 0,
  }
end

local function execute_pending(item, key)
  local input = nil
  pcall(function() input = item.object:get_field(item.field_name) end)
  if not input then return false end
  local selected = nil
  pcall(function() selected = as_int(input:call("getSelectedIndex")) end)
  if selected ~= item.index then
    pcall(function() input:call("requestSelectIndex", item.index, 0) end)
    return false
  end
  local selected_item = nil
  pcall(function() selected_item = input:call("getSelectedItem") end)
  if not selected_item then return false end
  local ok = pcall(function()
    item.object:call(item.callback_name, selected_item, selected_item, item.index)
  end)
  if not ok then return false end
  completed[key] = true
  completed[item.action] = true
  log_line(string.format("DECIDE %s index=%d", item.action, item.index))
  return true
end

local function hook_post(type_name, method_name, callback)
  local definition = sdk.find_type_definition(type_name)
  local method = definition and definition:get_method(method_name) or nil
  if not method then log_line("MISS " .. type_name .. "." .. method_name); return end
  local object = nil
  sdk.hook(method, function(args)
    if not runtime_active or not cfg.enabled then
      object = nil
      return
    end
    object = sdk.to_managed_object(args[2])
  end, function(retval)
    if object then pcall(callback, object) end
    object = nil
    return retval
  end)
end

-- The notice is informational. Marking WarningDone preserves the rest of the
-- native LogoController sequence (save load, network boot, DLC checks, etc.).
do
  local definition = sdk.find_type_definition("app.LogoController")
  local method = definition and definition:get_method("doUpdate") or nil
  if method then
    sdk.hook(method, function(args)
      if not runtime_active or not cfg.enabled or not cfg.skip_autosave_notice then return end
      local controller = sdk.to_managed_object(args[2])
      local param = nil
      pcall(function() param = controller:call("get_Param") end)
      if param then pcall(function() param:set_field("_WarningDone", true) end) end
    end, function(retval) return retval end)
  end
end

hook_post("app.GUI010001", "onOpen", function(object)
  if cfg.enabled and cfg.skip_logo_movie then
    logo_movie = object
    logo_flow_done = {}
  end
end)

hook_post("app.GUI010001", "onClose", function()
  logo_movie = nil
end)

hook_post("app.GUI010100", "onOpen", function(object)
  if cfg.enabled then press_any_key = object end
end)

hook_post("app.GUI010101", "onOpen", function(object)
  queue_input(object, "_SelListInput", 0, "start game", "callback_ListDecide")
end)

hook_post("app.GUI010102", "onOpen", function(object)
  queue_input(object, "_DataListInput", cfg.save_index, "save slot", "callback_ListDecide")
end)

do
  local definition = sdk.find_type_definition("app.TitleController.cTitleMenu")
  local method = definition and definition:get_method("update") or nil
  if method then
    sdk.hook(method, function(args)
      if not runtime_active or not cfg.enabled then return end
      local object = sdk.to_managed_object(args[2])
      title_menu_object = object
      title_menu_flow = as_int(object:get_field("menu_flow"))
    end, function(retval) return retval end)
  end
end

local function finish_runtime()
  if not runtime_active then return end
  runtime_active = false
  pending = {}
  logo_movie = nil
  logo_flow_done = {}
  press_any_key = nil
  title_menu_object = nil

  if recommended_lobby_action then
    pcall(function() recommended_lobby_action:release() end)
    recommended_lobby_action = nil
  end

  log_line("FINISH startup runtime disabled")
end

local function start_recommended_lobby()
  local definition = sdk.find_type_definition("app.cGUICommonMenu_Lobby00")
  local callback = definition and definition:get_method("<execute>b__0_0") or nil
  if not callback then
    log_line("ERROR recommended lobby callback missing")
    return false
  end

  local action = nil
  local created, create_error = pcall(function()
    action = sdk.create_instance("app.cGUICommonMenu_Lobby00")
  end)
  if not created or not action then
    log_line("ERROR recommended lobby action creation: " .. tostring(create_error))
    return false
  end

  -- Keep the menu action alive while native matchmaking and its progress GUI
  -- retain it as their owner. Lobby00 index 0 is the native Yes callback: it
  -- starts NetworkRequestManager.autoMatching and lets TitleMenu await success.
  pcall(function()
    local rooted = action:add_ref()
    if rooted then action = rooted end
  end)
  local ok = pcall(function() callback:call(action, 0) end)
  if not ok then
    pcall(function() action:release() end)
    log_line("ERROR recommended lobby native callback")
    return false
  end

  recommended_lobby_action = action
  log_line("DECIDE recommended lobby via native autoMatching")
  return true
end

re.on_application_entry("UpdateBehavior", function()
  if not runtime_active or not cfg.enabled then return end
  update_frame = update_frame + 1

  -- FINISH_END means the native title flow has completed matchmaking and its
  -- scene transition. From here onward this mod becomes a single boolean
  -- guard; it retains no UI or matchmaking objects and performs no polling.
  if title_menu_flow == 92 then
    finish_runtime()
    return
  end

  if logo_movie then
    local flow = nil
    pcall(function() flow = as_int(logo_movie:get_field("_Flow")) end)
    if flow ~= nil and not logo_flow_done[flow] then
      logo_flow_done[flow] = true
      if pcall(function() logo_movie:call("onEndMovie") end) then
        log_line("SKIP logo flow=" .. tostring(flow))
      end
    end
  end

  if press_any_key then
    local rno = nil
    pcall(function() rno = as_int(press_any_key:get_field("_Rno")) end)
    if rno == 2 then
      local title = press_any_key
      press_any_key = nil
      if pcall(function() title:call("callback_ListTrigger", 0, nil, nil, 0) end) then
        log_line("DECIDE press any key")
      else
        log_line("ERROR press any key callback")
      end
    end
  end

  if title_menu_flow == 71 and title_menu_object
      and not completed["select recommended lobby"]
      and recommended_lobby_attempts < 3
      and update_frame >= recommended_lobby_retry_frame then
    recommended_lobby_attempts = recommended_lobby_attempts + 1
    recommended_lobby_retry_frame = update_frame + 60
    if start_recommended_lobby() then
      completed["select recommended lobby"] = true
    end
  end

  for key, item in pairs(pending) do
    item.attempts = item.attempts + 1
    if execute_pending(item, key) or item.attempts > 600 then
      if item.attempts > 600 then log_line("TIMEOUT " .. item.action) end
      pending[key] = nil
    end
  end
end)

re.on_draw_ui(function()
  if not imgui.tree_node(MOD .. " v" .. VERSION) then return end
  local changed
  changed, cfg.enabled = imgui.checkbox("Auto start recommended lobby", cfg.enabled)
  changed, cfg.skip_logo_movie = imgui.checkbox("Skip skippable logo movie", cfg.skip_logo_movie)
  changed, cfg.skip_autosave_notice = imgui.checkbox("Skip autosave notice", cfg.skip_autosave_notice)
  imgui.text("Save slot: 1 | Lobby: Recommended")
  imgui.text("Runtime active: " .. tostring(runtime_active))
  imgui.text("Title flow: " .. tostring(title_menu_flow))
  imgui.tree_pop()
end)

log_line("===== LOADED v" .. VERSION .. " =====")
