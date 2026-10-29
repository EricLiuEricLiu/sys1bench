const RANKED_ENTRIES = `
WITH humans AS (
  SELECT participant_id,correct,total,
    ROW_NUMBER() OVER (ORDER BY completed_at,run_id) AS human_number
  FROM human_first_results WHERE cohort=?
), entries AS (
  SELECT 'human' AS kind,0 AS is_you,human_number,NULL AS model_id,correct,total
  FROM humans WHERE (? IS NULL OR participant_id<>?)
  UNION ALL
  SELECT 'ai',0,NULL,json_extract(value,'$.modelId'),
    json_extract(value,'$.correct'),json_extract(value,'$.total')
  FROM json_each(?)
  UNION ALL
  SELECT 'human',1,
    COALESCE((SELECT human_number FROM humans WHERE participant_id=?),(SELECT COUNT(*)+1 FROM humans)),
    NULL,?,? WHERE ?=1
), ranked AS (
  SELECT *,RANK() OVER (ORDER BY 1.0*correct/total DESC) AS rank,
    ROW_NUMBER() OVER (ORDER BY 1.0*correct/total DESC,
      CASE kind WHEN 'human' THEN 0 ELSE 1 END,human_number,model_id) AS position,
    COUNT(*) OVER () AS total_entries
  FROM entries
), bounds AS (
  SELECT MAX(CASE WHEN is_you=1 THEN position END) AS viewer_position FROM ranked
)
SELECT kind,is_you,human_number,model_id,correct,total,rank,position,total_entries
FROM ranked CROSS JOIN bounds
WHERE total_entries<=20 OR is_you=1 OR kind='ai' OR position<=3
  OR position>total_entries-2 OR position BETWEEN viewer_position-2 AND viewer_position+2
ORDER BY position`;

export async function getLeaderboard(DB,{cohort,datasetVersion,protocol,modelResults,viewer=null}) {
  const models=modelResults.filter(m=>m.real===true && m.datasetVersion===datasetVersion && m.humanProtocol===protocol)
    .map(m=>({modelId:m.modelId,name:m.name,protocol:m.protocol,correct:m.correct,total:m.total,unanswered:m.unanswered,evaluatedAt:m.evaluatedAt,condition:m.condition,runId:m.runId,inputNotes:m.inputNotes,failures:m.failures}))
    .sort((a,b)=>b.correct/b.total-a.correct/a.total);
  const [aggregate,distribution,ranked]=await Promise.all([
    DB.prepare('SELECT COUNT(*) AS count,AVG(1.0*correct/total) AS accuracy FROM human_first_results WHERE cohort=?').bind(cohort).first(),
    DB.prepare('SELECT correct,COUNT(*) AS count FROM human_first_results WHERE cohort=? GROUP BY correct ORDER BY correct DESC').bind(cohort).all(),
    DB.prepare(RANKED_ENTRIES).bind(cohort,viewer?.participantId??null,viewer?.participantId??null,
      JSON.stringify(models),viewer?.participantId??null,viewer?.correct??null,viewer?.total??null,viewer?1:0).all(),
  ]);
  const byId=new Map(models.map(m=>[m.modelId,m]));
  const entries=ranked.results.map(row=>({
    key:row.is_you?'you':row.kind==='ai'?`ai:${row.model_id}`:`human:${row.human_number}`,
    kind:row.kind,name:row.is_you?'You':row.kind==='ai'?byId.get(row.model_id).name:`Human ${row.human_number}`,
    correct:row.correct,total:row.total,rank:row.rank,position:row.position,isYou:Boolean(row.is_you),
    ...(row.kind==='ai'?{modelId:row.model_id,unanswered:byId.get(row.model_id).unanswered,failures:byId.get(row.model_id).failures}:{}),
  }));
  const totalEntries=ranked.results[0]?.total_entries??0;
  return {cohort,datasetVersion,protocol,humans:{...aggregate,distribution:distribution.results},models,
    entries,totalEntries,abbreviated:entries.length<totalEntries,viewer:viewer?{isRepeat:viewer.isRepeat}:null,pilot:true};
}
