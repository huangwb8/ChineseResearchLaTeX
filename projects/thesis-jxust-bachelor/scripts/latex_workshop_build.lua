#!/usr/bin/env texlua

local is_windows = package.config:sub(1, 1) == "\\"

local function write_stderr(message)
  io.stderr:write(message, "\n")
end

local function file_exists(path)
  local handle = io.open(path, "rb")
  if handle == nil then
    return false
  end
  handle:close()
  return true
end

local function quote_posix(arg)
  return "'" .. tostring(arg):gsub("'", "'\\''") .. "'"
end

local function quote_windows(arg)
  arg = tostring(arg)
  if arg == "" then
    return '""'
  end
  if not arg:find('[ \t"&|<>^()]') then
    return arg
  end

  local pieces = { '"' }
  local pending_backslashes = 0
  for index = 1, #arg do
    local char = arg:sub(index, index)
    if char == "\\" then
      pending_backslashes = pending_backslashes + 1
    elseif char == '"' then
      table.insert(pieces, string.rep("\\", pending_backslashes * 2 + 1))
      table.insert(pieces, '"')
      pending_backslashes = 0
    else
      if pending_backslashes > 0 then
        table.insert(pieces, string.rep("\\", pending_backslashes))
        pending_backslashes = 0
      end
      table.insert(pieces, char)
    end
  end

  if pending_backslashes > 0 then
    table.insert(pieces, string.rep("\\", pending_backslashes * 2))
  end
  table.insert(pieces, '"')
  return table.concat(pieces)
end

local function quote(arg)
  if is_windows then
    return quote_windows(arg)
  end
  return quote_posix(arg)
end

local function join_command(tokens)
  local quoted = {}
  for index, token in ipairs(tokens) do
    quoted[index] = quote(token)
  end
  return table.concat(quoted, " ")
end

local function command_succeeded(ok, _, code)
  if type(ok) == "number" then
    return ok == 0, ok
  end
  if ok == true then
    return true, code or 0
  end
  return false, code or 1
end

local function command_exists(tokens)
  local probe = {}
  for index, token in ipairs(tokens) do
    probe[index] = token
  end
  probe[#probe + 1] = "--version"

  local redirect = is_windows and ">NUL 2>&1" or ">/dev/null 2>&1"
  local ok, kind, code = os.execute(join_command(probe) .. " " .. redirect)
  return command_succeeded(ok, kind, code)
end

local function add_candidate(candidates, seen, tokens)
  local key = table.concat(tokens, "\0")
  if seen[key] then
    return
  end
  seen[key] = true
  candidates[#candidates + 1] = tokens
end

local function add_virtual_env_candidate(candidates, seen, env_root)
  if env_root == nil or env_root == "" then
    return
  end
  local suffix = is_windows and "\\Scripts\\python.exe" or "/bin/python"
  add_candidate(candidates, seen, { env_root .. suffix })
end

local function list_python_candidates()
  local candidates = {}
  local seen = {}

  local override = os.getenv("BENSZ_VSCODE_PYTHON")
  if override ~= nil and override ~= "" then
    add_candidate(candidates, seen, { override })
  end

  add_virtual_env_candidate(candidates, seen, os.getenv("VIRTUAL_ENV"))
  add_virtual_env_candidate(candidates, seen, os.getenv("CONDA_PREFIX"))

  if is_windows then
    add_candidate(candidates, seen, { "py", "-3" })
    add_candidate(candidates, seen, { "python" })
    add_candidate(candidates, seen, { "python3" })
  else
    add_candidate(candidates, seen, { "python3" })
    add_candidate(candidates, seen, { "python" })
  end

  return candidates
end

local function find_python_command()
  local attempted = {}

  for _, candidate in ipairs(list_python_candidates()) do
    attempted[#attempted + 1] = join_command(candidate)
    local executable = candidate[1]
    if executable:find("[/\\]") and not file_exists(executable) then
      goto continue
    end
    if command_exists(candidate) then
      return candidate, attempted
    end
    ::continue::
  end

  return nil, attempted
end

local script_path = arg[1]
if script_path == nil or script_path == "" then
  write_stderr("latex_workshop_build.lua 用法：texlua latex_workshop_build.lua <python-script> [args...]")
  os.exit(2)
end

local python_command, attempted = find_python_command()
if python_command == nil then
  write_stderr("未找到可用的 Python 3 解释器。")
  write_stderr("已尝试：" .. table.concat(attempted, " | "))
  write_stderr("可通过环境变量 BENSZ_VSCODE_PYTHON 指定解释器绝对路径。")
  os.exit(1)
end

local command = {}
for _, token in ipairs(python_command) do
  command[#command + 1] = token
end
command[#command + 1] = script_path
for index = 2, #arg do
  command[#command + 1] = arg[index]
end

local ok, kind, code = os.execute(join_command(command))
local succeeded, exit_code = command_succeeded(ok, kind, code)
if succeeded then
  os.exit(0)
end
os.exit(exit_code)
