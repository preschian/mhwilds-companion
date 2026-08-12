-- FieldGuideSOS
-- F1 = auto | F8 = start log | F9 = stop log
-- Crash: setQuestListInCategory(12) AFTER search = CRASH
-- Safe: setQuestListInCategory(12) ONLY before search; after search use soft set_ViewCategory
-- Popup: skip LOCAL_SESSION_NOT_FOUND + skip openDialog_faildSearchQuest (no Invoke, no cat rewrite)
-- Depart: settle after join before decideDepartLate/QuestDepart

local MOD = "FieldGuideSOS"
local VERSION = "1.4.7"

local VK_F1, VK_F8, VK_F9, VK_ESC = 0x70, 0x77, 0x78, 0x1B
local UI050000, UI050001, UI050002 = 161, 162, 163
local UI060000, UI060001 = 169, 170
local UI060102 = 179
local ALMA_IDS = { 161, 162, 163, 164, 165 }

local ARKVELD_ID = 27
local ROLE_NORMAL = 0
local LEGENDARY_TEMPERED = 1
local DIFF_HIGH_NATIVE = 300
local QUEST_TYPE_ANY = 0
local FIELD_ANY = -1
local MISSION_INVALID = 4294967295
local CAT_SEARCH_RESCUE = 12
local QC_MODE_NORMAL = 0
local ERR_LOCAL_SESSION_NOT_FOUND = 110002 -- NETWORK_ERROR_CODE.LOCAL_SESSION_NOT_FOUND

local LOG_FILE = "fieldguide_sos_trace.txt"
local cfg = {
  auto_depart = true,
  action_gap_s = 1.0,
  wait_alma_s = 12,
  wait_list_s = 15,
  wait_join_s = 35,
  depart_settle_s = 1.0,
  retry_search_s = 3,
  max_search = 8,
  em_id = ARKVELD_ID,
}

local state = {
  phase = "idle",
  msg = "F1=auto | F8=log | F9=stop",
  searches = 0,
  deadline = 0,
  next_action_at = 0,
  ordered = false,
  suppress_popup = false, -- skip LOCAL_SESSION_NOT_FOUND + openDialog_faildSearchQuest
  depart_ready_at = 0,
}

local tracing = false
local lines = {}
local counts = {}
local MAX_LINES = 14
local session_n = 0
local alma_open_now = false
local last_alma = false
local keys = { f1 = false, f8 = false, f9 = false, esc = false }

local function modlog(msg)
  local s = "[" .. MOD .. "] " .. tostring(msg)
  if type(log) == "table" and type(log.info) == "function" then log.info(s)
  elseif type(log) == "function" then log(s)
  else print(s) end
end

local function write_file(line)
  pcall(function()
    local f = io.open(LOG_FILE, "a")
    if not f then return end
    f:write(os.date("%H:%M:%S ") .. tostring(line) .. "\n")
    f:close()
  end)
end

local function note(msg)
  state.msg = tostring(msg)
  modlog(state.msg)
  write_file(state.msg)
end

local function set_phase(phase, msg)
  state.phase = phase
  if phase == "idle" or phase == "done" or phase == "error" then
    state.suppress_popup = false
  end
  note(phase .. " | " .. tostring(msg or ""))
end

local function action_ready()
  local now = os.clock()
  if now < state.next_action_at then
    state.msg = string.format("jeda %.1fs...", state.next_action_at - now)
    return false
  end
  return true
end

local function arm_gap()
  state.next_action_at = os.clock() + cfg.action_gap_s
end

local function get_gui_manager()
  return sdk.get_managed_singleton("app.GUIManager")
end

local function is_open(id)
  local gm = get_gui_manager()
  if not gm then return false end
  local open = false
  pcall(function() open = gm:call("isOpenGUI", id) end)
  return open and true or false
end

local function is_alma_open()
  for _, id in ipairs(ALMA_IDS) do
    if is_open(id) then return true end
  end
  return false
end

local function get_gui(id)
  local gm = get_gui_manager()
  if not gm then return nil end
  local gui = nil
  pcall(function() gui = gm:call("getGUI", id) end)
  return gui
end

local function to_int(v)
  if v == nil then return nil end
  if type(v) == "number" then return math.floor(v) end
  local ok, n = pcall(sdk.to_int64, v)
  if ok and n ~= nil then return tonumber(n) end
  return tonumber(tostring(v))
end

local function key_down(vk)
  local down = false
  pcall(function() down = reframework:is_key_down(vk) end)
  return down and true or false
end

----------------------------------------------------------------
-- Tracer
----------------------------------------------------------------
local function tpush(msg)
  if not tracing then return end
  local t = string.format("%s %s", os.date("%H:%M:%S"), tostring(msg))
  lines[#lines + 1] = t
  while #lines > MAX_LINES do table.remove(lines, 1) end
  modlog(msg)
  write_file(t)
end

local function tbump(key)
  if not tracing then return 0 end
  counts[key] = (counts[key] or 0) + 1
  return counts[key]
end

local function start_trace()
  if tracing then return end
  tracing = true
  session_n = session_n + 1
  lines, counts = {}, {}
  write_file("")
  write_file(string.format("===== CAPTURE START session=%d %s =====", session_n, os.date("%Y-%m-%d %H:%M:%S")))
  tpush("TRACE START")
end

local function stop_trace()
  if not tracing then return end
  tpush("TRACE STOP")
  write_file("-- counts --")
  for k, v in pairs(counts) do write_file(string.format("%d  %s", v, k)) end
  write_file(string.format("===== CAPTURE STOP session=%d =====", session_n))
  tracing = false
end

local function dump_search(search)
  if not search then return "nil" end
  local bits = {}
  pcall(function() bits[#bits+1] = "resc=" .. tostring(search:call("get_Rescure")) end)
  pcall(function() bits[#bits+1] = "diff=" .. tostring(search:call("get_QuestDifficulty")) end)
  local t = nil
  pcall(function() t = search:call("get_Target") end)
  if t then
    pcall(function() bits[#bits+1] = "tid=" .. tostring(t:get_field("Id")) end)
    pcall(function() bits[#bits+1] = "role=" .. tostring(t:get_field("RoleId")) end)
    pcall(function() bits[#bits+1] = "leg=" .. tostring(t:get_field("LegendaryId")) end)
  end
  return table.concat(bits, " ")
end

local function dump_view(view)
  if not view then return "nil" end
  local bits = {}
  pcall(function() bits[#bits+1] = "mid=" .. tostring(view:call("get_MissionID")) end)
  local session = nil
  pcall(function() session = view:get_field("Session") end)
  if session then
    pcall(function() bits[#bits+1] = "sid=" .. tostring(session:call("get_QuestSessionID")) end)
    local sr = nil
    pcall(function() sr = session:call("get_SearchResult") end)
    bits[#bits+1] = "hasSR=" .. tostring(sr ~= nil)
  else
    bits[#bits+1] = "session=nil"
  end
  return table.concat(bits, " ")
end

local function hook(type_name, method_name, fmt_fn)
  local t = sdk.find_type_definition(type_name)
  if not t then return end
  local m = t:get_method(method_name)
  if not m then return end
  local key = type_name .. "." .. method_name
  sdk.hook(m, function(args)
    if not tracing then return end
    local n = tbump(key)
    local extra = ""
    if fmt_fn then
      local ok, s = pcall(fmt_fn, args)
      if ok and s then extra = " | " .. s end
    end
    local leaf = type_name:match("([^.]+)$") or type_name
    tpush(string.format("#%d %s.%s%s", n, leaf, method_name, extra))
  end, function(retval) return retval end)
end

local function skip_original()
  if sdk.PreHookResult and sdk.PreHookResult.SKIP_ORIGINAL ~= nil then
    return sdk.PreHookResult.SKIP_ORIGINAL
  end
  return nil
end

-- Popup handling (1.4.7 = 1.4.5 PREVENT, no REWRITE, no Invoke):
-- Skip NetworkErrorManager LOCAL_SESSION_NOT_FOUND.
-- Skip openDialog_faildSearchQuest UI only (do NOT Invoke close Action — that broke wait_order).
-- Do NOT rewrite setQuestListCategory (REWRITE crashed at depart).
local function hook_skip_session_popup()
  local t = sdk.find_type_definition("app.NetworkErrorManager")
  if t then
    for _, m in ipairs(t:get_methods() or {}) do
      local name = m:get_name()
      if name == "requestAppError" or name == "showError" or name == "showErrorRequest" then
        sdk.hook(m, function(args)
          if not state.suppress_popup then return end
          local code = to_int(args[4])
          if code == nil then code = to_int(args[3]) end
          if code == ERR_LOCAL_SESSION_NOT_FOUND then
            note("PREVENT popup LOCAL_SESSION_NOT_FOUND")
            if tracing then tpush("SKIP NetworkErrorManager." .. name) end
            return skip_original()
          end
        end, function(retval) return retval end)
      end
    end
  end

  local t2 = sdk.find_type_definition("app.GUI050000")
  if t2 then
    local m = t2:get_method("openDialog_faildSearchQuest")
    if m then
      sdk.hook(m, function(args)
        if not state.suppress_popup then return end
        note("PREVENT openDialog_faildSearchQuest")
        if tracing then tpush("SKIP openDialog_faildSearchQuest") end
        return skip_original()
      end, function(retval) return retval end)
    end
  end
end

local function hook_trace_category_only()
  local t = sdk.find_type_definition("app.GUI050000")
  if not t then return end
  local m = t:get_method("setQuestListCategory")
  if not m then return end
  sdk.hook(m, function(args)
    if not tracing then return end
    local cat = to_int(args[3])
    local n = tbump("app.GUI050000.setQuestListCategory")
    tpush(string.format("#%d setQuestListCategory | cat=%s", n, tostring(cat)))
  end, function(retval) return retval end)
end

hook("app.GUI050000", "search", function(args) return dump_search(sdk.to_managed_object(args[3])) end)
hook("app.GUI050000", "setQuestListInCategory", function(args) return "cat=" .. tostring(to_int(args[3])) end)
hook("app.GUI050000", "changeCategorySelectedIndex", function(args) return "cat=" .. tostring(to_int(args[3])) end)
hook("app.net_quest_session.QuestMatchmakeSystem", "SearchRescure", function(args) return dump_search(sdk.to_managed_object(args[3])) end)
hook("app.net_quest_session.QuestMatchmakeSystem", "JoinSession", function() return "JoinSession" end)
hook("app.net_quest_session.cQuestSession", "joinSession", function() return "joinSession" end)
hook("app.GUI050000QuestListParts", "updateQuestDetailWindow", function(args) return dump_view(sdk.to_managed_object(args[3])) end)
hook("app.GUI050000QuestListParts", "decideQuest", function(args) return dump_view(sdk.to_managed_object(args[3])) end)
hook("app.GUI050000QuestListParts", "set_ViewCategory", function(args) return "cat=" .. tostring(to_int(args[3])) end)
hook("app.GUI050001", "orderQuest", function() return "orderQuest" end)
hook("app.cGUIQuestOrderHelper", "order", function(args) return "orderType=" .. tostring(to_int(args[4])) end)
hook("app.cGUIQuestOrderHelper", "executeJoinSession", function() return "executeJoinSession" end)
hook("app.GUIManager", "requestQuestCounter", function() return "requestQuestCounter" end)
hook("app.GUIManager", "setQuestOrderParam", function() return "param set" end)
hook("app.GUI050002", "QuestDepart", function() return "QuestDepart" end)
hook("app.GUI050002_DeparturePreparingLink", "decideDepartLate", function() return "departLate" end)

hook_skip_session_popup()
hook_trace_category_only()

----------------------------------------------------------------
-- Auto helpers
----------------------------------------------------------------
local function resolve_em_id()
  if cfg.em_id and cfg.em_id > 0 then return cfg.em_id end
  local gui = get_gui(UI060102)
  if gui then
    local id = nil
    pcall(function() id = to_int(gui:call("get_TargetEmId")) end)
    if id and id > 0 then return id end
  end
  return ARKVELD_ID
end

local function open_alma()
  local gm = get_gui_manager()
  if not gm then return false, "no GUIManager" end
  note("CALL requestQuestCounter(NORMAL)")
  local ok = pcall(function() gm:call("requestQuestCounter", QC_MODE_NORMAL) end)
  return ok, ok and "requestQuestCounter" or "open Alma failed"
end

local function build_search(em_id)
  local info = sdk.create_instance("app.net_quest_session.cSearchQuestSessionInfo")
  if not info then return nil end
  info = info:add_ref()
  pcall(function() info:call(".ctor") end)
  local target = sdk.create_instance("app.net_quest_session.cSearchQuestSessionInfo.cTargetInfo")
  if not target then return nil end
  target = target:add_ref()
  pcall(function() target:call(".ctor") end)
  target:set_field("Id", em_id)
  target:set_field("RoleId", ROLE_NORMAL)
  target:set_field("LegendaryId", LEGENDARY_TEMPERED)
  info:call("set_Rescure", true)
  info:call("set_QuestDifficulty", DIFF_HIGH_NATIVE)
  info:call("set_QuestType", QUEST_TYPE_ANY)
  info:set_field("FieldId", FIELD_ANY)
  info:call("set_IsSameLanguage", false)
  info:call("set_IsSamePlatform", false)
  info:call("set_QuestNo", 0)
  info:call("set_Target", target)
  return info
end

local function do_search()
  local gui = get_gui(UI050000)
  if not gui then return false, "no GUI050000" end
  local em = resolve_em_id()
  local info = build_search(em)
  if not info then return false, "build search failed" end
  note("CALL GUI050000.search tid=" .. tostring(em))
  local ok, err = pcall(function() gui:call("search", info, MISSION_INVALID) end)
  if not ok then return false, "search err: " .. tostring(err) end
  return true, "search ok tid=" .. tostring(em)
end

local function list_count(list)
  if not list then return 0 end
  local n = 0
  pcall(function() n = list:call("get_Count") end)
  if n == 0 then pcall(function() n = list:get_field("_size") end) end
  return tonumber(n) or 0
end

local function list_get(list, i)
  if not list then return nil end
  local item = nil
  pcall(function() item = list:call("get_Item", i) end)
  return item
end

local function get_parts()
  local gui = get_gui(UI050000)
  if not gui then return nil end
  local parts = nil
  pcall(function() parts = gui:get_field("_QuestListParts") end)
  return parts
end

local function current_category()
  local parts = get_parts()
  if not parts then return nil end
  local cat = nil
  pcall(function() cat = to_int(parts:call("get_ViewCategory")) end)
  return cat
end

-- SAFE only BEFORE search
local function force_cat_pre_search()
  local gui = get_gui(UI050000)
  if not gui then return false, "no GUI050000" end
  note("CALL setQuestListInCategory(12) [pre-search]")
  local ok, err = pcall(function() gui:call("setQuestListInCategory", CAT_SEARCH_RESCUE) end)
  if not ok then return false, tostring(err) end
  return true, "cat=12"
end

-- SAFE after search (do NOT use setQuestListInCategory)
local function soft_cat_post_search()
  local parts = get_parts()
  if parts then
    note("CALL set_ViewCategory(12) [post-search soft]")
    local ok = pcall(function() parts:call("set_ViewCategory", CAT_SEARCH_RESCUE) end)
    if ok then return true, "set_ViewCategory" end
  end
  local gui = get_gui(UI050000)
  if gui then
    note("CALL changeCategorySelectedIndex(12) [post-search soft]")
    local ok = pcall(function() gui:call("changeCategorySelectedIndex", CAT_SEARCH_RESCUE) end)
    if ok then return true, "changeCategorySelectedIndex" end
  end
  return true, "skip soft cat"
end

local function view_has_sr(view)
  if not view then return false end
  local session = nil
  pcall(function() session = view:get_field("Session") end)
  if not session then return false end
  local sr = nil
  pcall(function() sr = session:call("get_SearchResult") end)
  return sr ~= nil
end

local function pick_rescue_view()
  local parts = get_parts()
  if not parts then return nil, nil, "no parts" end
  local list = nil
  pcall(function() list = parts:call("getQuestViewDataList_SearchRescueSignal") end)
  if list_count(list) < 1 then
    pcall(function() list = parts:call("get_ViewQuestDataList") end)
  end
  local n = list_count(list)
  for i = 0, math.max(n - 1, -1) do
    local view = list_get(list, i)
    if view_has_sr(view) then
      return view, parts, "idx=" .. i .. " n=" .. n
    end
  end
  return nil, nil, "no hasSR n=" .. tostring(n)
end

local function do_detail()
  local view, parts, detail = pick_rescue_view()
  if not view then return false, tostring(detail) end
  note("CALL updateQuestDetailWindow " .. tostring(detail))
  local ok, err = pcall(function() parts:call("updateQuestDetailWindow", view) end)
  if not ok then return false, "detail: " .. tostring(err) end
  return true, "detail " .. dump_view(view)
end

local function do_decide()
  local view, parts, detail = pick_rescue_view()
  if not view then return false, tostring(detail) end
  note("CALL decideQuest " .. tostring(detail))
  local ok, err = pcall(function() parts:call("decideQuest", view) end)
  if not ok then return false, "decide: " .. tostring(err) end
  return true, "decide " .. dump_view(view)
end

local function do_order()
  local gui = get_gui(UI050001)
  if not gui then return false, "no GUI050001" end
  note("CALL orderQuest")
  local ok, err = pcall(function() gui:call("orderQuest") end)
  if not ok then return false, "order: " .. tostring(err) end
  return true, "orderQuest"
end

local function is_rescue_session()
  local ok, v = pcall(function()
    return sdk.find_type_definition("app.GUIUtilApp.QuestUtil"):get_method("isResucureSession"):call(nil)
  end)
  return ok and v and true or false
end

local function camp_info_ready()
  return is_open(UI060000) and is_open(UI060001)
end

local function camp_visible()
  return is_open(UI060000) or is_open(UI060001) or is_open(UI050002)
end

local function do_depart()
  if not is_rescue_session() then return false, "wait session" end
  local gui = get_gui(UI050002)
  if not gui then return false, "wait GUI050002" end
  -- Late-join path only: call decideDepartLate when link exists, then QuestDepart.
  -- If decideDepartLate fails, do not call QuestDepart (avoids half-state crash).
  local link = nil
  pcall(function() link = gui:get_field("_DeparturePreparingLink") end)
  if link then
    note("CALL decideDepartLate")
    local ok, err = pcall(function() link:call("decideDepartLate") end)
    if not ok then return false, "departLate: " .. tostring(err) end
  else
    note("skip decideDepartLate (no link)")
  end
  note("CALL QuestDepart")
  local ok2, err2 = pcall(function() gui:call("QuestDepart") end)
  if not ok2 then return false, "QuestDepart: " .. tostring(err2) end
  return true, "depart"
end

local function cancel_auto()
  state.suppress_popup = false
  set_phase("idle", "cancelled")
  state.searches = 0
  state.deadline = 0
  state.next_action_at = 0
  state.ordered = false
  state.depart_ready_at = 0
end

local function start_auto()
  state.searches = 0
  state.next_action_at = 0
  state.ordered = false
  state.suppress_popup = false
  state.depart_ready_at = 0
  write_file("===== AUTO START v" .. VERSION .. " " .. os.date("%Y-%m-%d %H:%M:%S") .. " =====")
  if is_alma_open() then
    arm_gap()
    set_phase("prep_cat", "Alma open")
  else
    local ok, detail = open_alma()
    arm_gap()
    if not ok then set_phase("error", detail) return end
    state.deadline = os.clock() + cfg.wait_alma_s
    set_phase("wait_alma", detail)
  end
end

local function tick_auto()
  local phase = state.phase
  if phase == "idle" or phase == "done" or phase == "error" then return end
  local now = os.clock()

  if phase == "wait_alma" then
    if is_open(UI050000) or is_alma_open() then
      if not action_ready() then return end
      arm_gap()
      set_phase("prep_cat", "Alma open")
      return
    end
    if now > state.deadline then set_phase("error", "timeout Alma") end
    return
  end

  if phase == "prep_cat" then
    if not action_ready() then return end
    if current_category() == CAT_SEARCH_RESCUE then
      arm_gap()
      set_phase("search", "already cat=12")
      return
    end
    local ok, detail = force_cat_pre_search()
    arm_gap()
    if not ok then set_phase("error", detail) return end
    set_phase("search", detail)
    return
  end

  if phase == "search" then
    if not action_ready() then return end
    if not is_open(UI050000) then state.msg = "waiting GUI050000..." return end
    if current_category() ~= CAT_SEARCH_RESCUE then
      local ok, detail = force_cat_pre_search()
      arm_gap()
      if not ok then set_phase("error", detail) return end
      return
    end
    state.searches = state.searches + 1
    if state.searches > cfg.max_search then set_phase("error", "max search") return end
    state.suppress_popup = true -- from search until join
    local ok, detail = do_search()
    arm_gap()
    if not ok then
      state.suppress_popup = false
      set_phase("error", detail)
      return
    end
    state.deadline = now + cfg.wait_list_s
    set_phase("post_search", detail)
    return
  end

  if phase == "post_search" then
    if not action_ready() then return end
    note("post_search cat=" .. tostring(current_category()))
    -- never setQuestListInCategory here
    soft_cat_post_search()
    arm_gap()
    set_phase("wait_list", "wait hasSR")
    return
  end

  if phase == "wait_list" then
    local view, _, detail = pick_rescue_view()
    if view then
      if not action_ready() then
        state.msg = string.format("hasSR jeda %.1fs cat=%s", math.max(0, state.next_action_at - now), tostring(current_category()))
        return
      end
      set_phase("detail", tostring(detail))
      return
    end
    state.msg = "wait hasSR cat=" .. tostring(current_category()) .. " " .. tostring(detail)
    if now > state.deadline then
      state.deadline = now + cfg.retry_search_s
      set_phase("prep_cat", "retry")
    end
    return
  end

  if phase == "detail" then
    if not action_ready() then return end
    local ok, detail = do_detail()
    arm_gap()
    if not ok then
      state.msg = tostring(detail)
      if now > state.deadline then set_phase("prep_cat", "detail fail") end
      return
    end
    set_phase("decide", detail)
    return
  end

  if phase == "decide" then
    if not action_ready() then return end
    local ok, detail = do_decide()
    arm_gap()
    if not ok then
      state.msg = tostring(detail)
      if now > state.deadline then set_phase("prep_cat", "decide fail") end
      return
    end
    state.deadline = now + cfg.wait_join_s
    state.ordered = false
    set_phase("wait_order", detail)
    return
  end

  if phase == "wait_order" then
    if state.ordered and is_rescue_session() then
      if not action_ready() then return end
      arm_gap()
      state.suppress_popup = false -- join ok; allow real errors again
      state.depart_ready_at = now + cfg.depart_settle_s
      state.deadline = now + cfg.wait_join_s
      set_phase("wait_depart", "joined; settle " .. tostring(cfg.depart_settle_s) .. "s")
      return
    end
    if not state.ordered then
      if not is_open(UI050001) then
        state.msg = "waiting 162..."
      elseif not camp_info_ready() then
        state.msg = "waiting 169+170..."
      elseif not action_ready() then
        -- gap
      else
        local ok, detail = do_order()
        arm_gap()
        if not ok then set_phase("error", detail) return end
        state.ordered = true
        state.msg = detail .. " — wait JoinSession"
        return
      end
    else
      state.msg = "waiting session..."
    end
    if now > state.deadline then set_phase("error", "timeout join") end
    return
  end

  if phase == "wait_depart" then
    if not cfg.auto_depart then set_phase("done", "joined") return end
    if not is_rescue_session() then
      state.msg = "waiting session..."
      if now > state.deadline then set_phase("error", "timeout session") end
      return
    end
    if not camp_visible() and get_gui(UI050002) == nil then
      state.msg = "waiting camp..."
      if now > state.deadline then set_phase("error", "timeout camp") end
      return
    end
    if state.depart_ready_at > 0 and now < state.depart_ready_at then
      state.msg = string.format("depart settle %.1fs...", state.depart_ready_at - now)
      return
    end
    if get_gui(UI050002) == nil then
      state.msg = "waiting GUI050002..."
      return
    end
    if not action_ready() then return end
    local ok, detail = do_depart()
    arm_gap()
    if ok then
      state.suppress_popup = false
      set_phase("done", detail)
      write_file("===== AUTO DONE =====")
    elseif detail == "wait session" or detail == "wait GUI050002" then
      state.msg = detail
    else
      state.suppress_popup = false
      set_phase("error", detail)
    end
  end
end

local function poll_keys()
  local f1, f8, f9, esc = key_down(VK_F1), key_down(VK_F8), key_down(VK_F9), key_down(VK_ESC)
  if f1 and not keys.f1 then
    if state.phase == "idle" or state.phase == "done" or state.phase == "error" then
      start_auto()
    end
  end
  if f8 and not keys.f8 then start_trace() end
  if f9 and not keys.f9 then stop_trace() end
  if esc and not keys.esc then
    if state.phase ~= "idle" and state.phase ~= "done" then cancel_auto()
    elseif tracing then stop_trace() end
  end
  keys.f1, keys.f8, keys.f9, keys.esc = f1, f8, f9, esc
end

re.on_application_entry("UpdateBehavior", function() tick_auto() end)

re.on_frame(function()
  poll_keys()
  alma_open_now = is_alma_open()
  if tracing and alma_open_now ~= last_alma then
    tpush("alma=" .. tostring(alma_open_now))
  end
  last_alma = alma_open_now
  if not (draw and draw.text) then return end
  pcall(function()
    draw.text(string.format("[%s v%s] %s trace=%s", MOD, VERSION, state.phase, tostring(tracing)), 24, 20, 0xFFFFFFFF)
    draw.text(tostring(state.msg), 24, 40, 0xFFAAFFAA)
    draw.text("F1 auto | F8 log | F9 stop | Esc cancel", 24, 60, 0xFFAAAAAA)
    local y = 78
    for i = 1, #lines do
      draw.text(lines[i], 24, y, 0xFF88CCFF)
      y = y + 15
    end
  end)
end)

re.on_draw_ui(function()
  if not imgui.tree_node(MOD .. " v" .. VERSION) then return end
  imgui.text("phase: " .. state.phase)
  imgui.text_wrapped(state.msg)
  local _, auto_d = imgui.checkbox("auto_depart", cfg.auto_depart)
  cfg.auto_depart = auto_d
  local _, em = imgui.drag_int("em_id", cfg.em_id, 1, 0, 200)
  cfg.em_id = em
  if imgui.button("Start") then start_auto() end
  imgui.same_line()
  if imgui.button("Cancel") then cancel_auto() end
  imgui.tree_pop()
end)

modlog(VERSION .. " loaded")
write_file("===== MOD LOADED v" .. VERSION .. " =====")
