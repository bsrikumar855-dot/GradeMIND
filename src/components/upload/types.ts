export interface ExamDetails {
  title: string;
  subject: string;
  total_marks: number;
  exam_date: string;
}

export interface RubricCriterion {
  id: string;
  label: string;
  marks: number;
  required: boolean;
}

export interface UploadState {
  step: number;
  examDetails: ExamDetails;
  files: {
    questionPaper: File[];
    answerKey: File[];
  };
  rubric: RubricCriterion[];
}
