import "./index.css";
import { MyComposition } from "./Composition";
import { Cv } from "./cv/Cv";
import { CvGraficos } from "./cv/CvGraficos";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <CvGraficos />
      <Cv />
    </>
  );
};
