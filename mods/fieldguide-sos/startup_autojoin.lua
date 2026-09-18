-- StartupAutoJoin
-- Skip logos, jump TitleMenu to Recommended Lobby. Boot (DLC/network/save) still runs.

local MOD = "StartupAutoJoin"
local VERSION = "0.1.8"
local LOG_FILE = "startup_autojoin_v" .. VERSION .. ".txt"

local FLOW_LOBBY_SELECT_INIT = 70
local FLOW_LOBBY_SELECT = 71
local FLOW_FINISH_END = 92

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
local skipped_parts = {}
local recommended_lobby_action = nil
local recommended_lobby_attempts = 0
local recommended_lobby_retry_frame = 0
local update_frame = 0
local runtime_active = true
local jumped_title_menu = false

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
  sdk.hook(method, function(args)
    if not runtime_active or not cfg.enabled then return end
    thread.get_hook_storage()["this"] = sdk.to_managed_object(args[2])
  end, function(retval)
    local object = thread.get_hook_storage()["this"]
    if object then pcall(callback, object) end
    return retval
  end)
end

local function skip_flow_part(type_name, key)
  local definition = sdk.find_type_definition(type_name)
  local method = definition and definition:get_method("update") or nil
  if not method then log_line("MISS " .. type_name .. ".update"); return end
  sdk.hook(method, function(args)
    if not runtime_active or not cfg.enabled or skipped_parts[key] then return end
    local obj = sdk.to_managed_object(args[2])
    local owner = nil
    pcall(function() owner = obj:call("get_Owner") end)
    if not owner then pcall(function() owner = obj:get_field("_Owner") end) end
    if owner and pcall(function() owner:call("Next") end) then
      skipped_parts[key] = true
      log_line("SKIP " .. key)
    end
  end, function(retval) return retval end)
end

-- GUI010001: jump to COPYRIGHT and close.
do
  local t = sdk.find_type_definition("app.GUI010001")
  local on_open = t and t:get_method("onOpen()")
  local vis = t and t:get_method("guiVisibleUpdate()")
  if not on_open or not vis then
    log_line("MISS app.GUI010001 skip hooks")
  else
    sdk.hook(on_open, function(args)
      if not runtime_active or not cfg.enabled or not cfg.skip_logo_movie then return end
      thread.get_hook_storage()["this"] = sdk.to_managed_object(args[2])
    end, function(retval)
      local obj = thread.get_hook_storage()["this"]
      if obj then
        log_line("SKIP logo flow was " .. tostring(obj._Flow))
        obj._Flow = 5
        obj:toClose()
      end
      return retval
    end)
    sdk.hook(vis, function(args)
      if not runtime_active or not cfg.enabled or not cfg.skip_logo_movie then return end
      local obj = sdk.to_managed_object(args[2])
      if not obj then return end
      obj._Skip = true
      obj._EnableSkip = true
    end)
  end
end

-- Informational notice only. Leave LogoController save/network/DLC boot intact.
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

-- After LogoController finishes: skip title demo + press-any-key flow parts.
skip_flow_part("app.TitleController.cTitleDemoLoad", "title demo")
skip_flow_part("app.TitleController.cTitle", "title press")

hook_post("app.GUI010100", "onOpen", function(object)
  pcall(function() object:call("callback_ListTrigger", 0, nil, nil, 0) end)
  pcall(function() object:toClose() end)
  log_line("SKIP press any key")
end)

-- Fallback if TitleMenu jump does not skip these GUIs.
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
      local param = nil
      pcall(function() param = object:call("get_Param") end)
      if param then
        pcall(function() param:set_field("SaveIndex", cfg.save_index) end)
        pcall(function() param:set_field("_InitialStateIsGameStart", true) end)
      end
      if title_menu_flow and title_menu_flow < FLOW_LOBBY_SELECT_INIT then
        pcall(function() object:set_field("req_flow", FLOW_LOBBY_SELECT_INIT) end)
        if not jumped_title_menu then
          jumped_title_menu = true
          log_line("JUMP title menu req_flow=" .. tostring(FLOW_LOBBY_SELECT_INIT) .. " from " .. tostring(title_menu_flow))
        end
      end
    end, function(retval) return retval end)
  end
end

local function finish_runtime()
  if not runtime_active then return end
  runtime_active = false
  pending = {}
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

  if title_menu_flow == FLOW_FINISH_END then
    finish_runtime()
    return
  end

  local at_lobby = title_menu_flow == FLOW_LOBBY_SELECT_INIT or title_menu_flow == FLOW_LOBBY_SELECT
  if at_lobby and title_menu_object
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
