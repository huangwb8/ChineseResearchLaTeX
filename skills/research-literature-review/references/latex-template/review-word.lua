-- Pandoc's DOCX writer renders abstract metadata without a label.
function Meta(meta)
  if meta.abstract and pandoc.utils.type(meta.abstract) == 'Blocks' then
    local label = pandoc.utils.stringify(meta.lang or ''):match('^zh') and '摘要' or 'Abstract'
    table.insert(meta.abstract, 1, pandoc.Para({pandoc.Strong({pandoc.Str(label)})}))
  end
  return meta
end
