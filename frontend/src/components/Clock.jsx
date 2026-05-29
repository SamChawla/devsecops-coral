/**
 * Self-contained ticking clock. Isolating the 1s interval here means only this
 * tiny node re-renders every second instead of the whole dashboard tree.
 */
import { memo, useEffect, useState } from "react";
import { T } from "../theme/tokens.js";

function Clock() {
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span style={{ fontSize: 10, color: T.textMuted, fontFamily: T.mono, marginLeft: "auto" }}>
      {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
}

export default memo(Clock);
