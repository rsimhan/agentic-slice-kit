const HYPOTHESES = new Set([
  'concept','calculation','application','units','interpretation',
  'recall','connection','distraction','task_size','prerequisite','difficulty'
]);

const QUESTION_IDS = new Set([
  'formula','force_change','division','division_transfer','substitution',
  'application_transfer','unit','unit_transfer','identify','identify_transfer',
  'recall','recall_second','connection','connection_transfer',
  'distraction','distraction_second','task_size','task_size_second',
  'prerequisite','prerequisite_second','difficulty','difficulty_second'
]);

const plainObject = value =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

export function validateInterpretation(value) {
  if (!plainObject(value)) return false;
  if (Object.keys(value).some(k => !['classification','quote','note'].includes(k))) return false;
  return ['pass','fail','uncertain'].includes(value.classification)
    && typeof value.quote === 'string' && value.quote.length <= 1000
    && typeof value.note === 'string' && value.note.length <= 500;
}

export function validatePlan(value) {
  if (!plainObject(value)) return false;
  if (Object.keys(value).some(k => !['hypothesis','question_id','question'].includes(k))) return false;
  return HYPOTHESES.has(value.hypothesis)
    && QUESTION_IDS.has(value.question_id)
    && typeof value.question === 'string'
    && value.question.length >= 8
    && value.question.length <= 280;
}
