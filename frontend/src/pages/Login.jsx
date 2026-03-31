import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Header from "../components/Header";
import { authService } from "../services/authService";
import "./Styles.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const navigate = useNavigate();

  async function handleLogin(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      await authService.login(username, password);
      navigate("/admin");
    } catch {
      setErro("Usuário ou senha inválidos.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="pagina">
      <Header />

      <div className="conteudo">
        <div className="card">
          <h2>Login</h2>

          <form onSubmit={handleLogin}>
            <label>
              <span>Usuário</span>
              <input
                type="text"
                placeholder="Digite seu usuário"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>

            <label>
              <span>Senha</span>
              <input
                type="password"
                placeholder="Digite sua senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {erro && <p style={{ color: "red", fontSize: "0.875rem" }}>{erro}</p>}

            <Link to="/cadastro">Cadastrar-se</Link>

            <button className="btnEntrar" type="submit" disabled={carregando}>
              {carregando ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}