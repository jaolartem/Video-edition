import "./index.css";
import { MyComposition } from "./Composition";
import { CvGraficos } from "./cv/CvGraficos";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <CvGraficos />
    </>
  );
};
