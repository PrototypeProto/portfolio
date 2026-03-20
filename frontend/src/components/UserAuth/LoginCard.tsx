import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { useNavigate } from "react-router-dom";

export default function LoginCard() {
  const navigate = useNavigate();
  
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [err, setErr] = useState<boolean>(false);
  const [errMessage, setErrMessage] = useState<string | null>(null)

  const { handleLogin } = useAuth();

  const handleLoginSubmit = async () => {
    const res = await handleLogin({ username, password })
    if (res.ok) {
      navigate("/profile");
      setErr(false);
    } 
    // else if (res.statusCode == 401) {
    //   navigate('/account-pending-approval')
    //   setErr(false)
    // }
    setErrMessage(res.error);
    setErr(true);
  };

  return (
    <div className="login-card">
      <h1>Login</h1>

      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        type="text"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button onClick={handleLoginSubmit}>Log in</button><br/>
      {err && (<span>Failed to login, try again{" : " + errMessage}</span>)}

    </div>
  );
}
