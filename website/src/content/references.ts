interface ReferenceItem {
  id: number;
  title: string;
  url?: string;
}

export const REFERENCES: readonly ReferenceItem[] = [
  {
    id: 1,
    title: "IoT- and AI-informed urban air quality models for vehicle pollution monitoring",
    url: "https://arxiv.org/html/2511.00187v1"
  },
  {
    id: 2,
    title: "IoT- and AI-informed urban air quality models for vehicle pollution monitoring (PDF)",
    url: "https://arxiv.org/pdf/2511.00187"
  },
  {
    id: 3,
    title: "IoT based monitoring of air quality and traffic using regression analysis",
    url: "https://pure.ulster.ac.uk/files/93366854/Articulo_IoT_TFG_Accepted.pdf"
  },
  {
    id: 4,
    title: "Model Development for the Real-World Emission Factor",
    url: "https://www.mdpi.com/2071-1050/17/17/8014"
  },
  { id: 5, title: "EMEP/EEA air pollutant emission inventory guidebook 2019 — Update Oct. 2020" },
  { id: 6, title: "EMEP/EEA air pollutant emission inventory guidebook 2023 — Update 2024: Road transport" },
  { id: 7, title: "Mô hình phân tán ô nhiễm vi mô trong street canyon đô thị" },
  { id: 8, title: "Cảm biến chất lượng không khí chi phí thấp (Low-Cost Sensors)" },
  { id: 9, title: "Hiệu chỉnh dữ liệu cảm biến môi trường bằng Random Forest, GPR, SVM" },
  { id: 10, title: "Dung hợp dữ liệu cảm biến bằng Graph Neural Networks / Graph Attention Networks" }
] as const;
