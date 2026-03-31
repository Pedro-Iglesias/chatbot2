import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import api from "../services/api";

const LABELS = {
  LOGIN:   "🔐 Login",
  LOGOUT:  "🚪 Logout",
  CREATE:  "➕ Criação",
  UPDATE:  "✏️ Edição",
  DELETE:  "🗑️ Exclusão",
  REINDEX: "🔄 Reindexação",
};

export default function Metricas() {
  const [logs, setLogs]       = useState([]);
  const [erro, setErro]       = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/admin-logs/")
      .then((res) => setLogs(res.data))
      .catch(() => setErro("Erro ao carregar logs."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#222831" }}>
      <Sidebar tipo="admin" />

      <div style={{ flex: 1, padding: "30px", overflowY: "auto" }}>
        <h2 style={{ color: "#00adb5", fontFamily: "Poppins", marginBottom: "24px" }}>
          Registro de Ações Administrativas
        </h2>

        {loading && <p style={{ color: "#eeeeee", fontFamily: "Poppins" }}>Carregando...</p>}
        {erro    && <p style={{ color: "red",     fontFamily: "Poppins" }}>{erro}</p>}

        {!loading && !erro && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "Poppins" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #00adb5", color: "#00adb5", textAlign: "left" }}>
                <th style={{ padding: "10px" }}>Data/Hora</th>
                <th style={{ padding: "10px" }}>Usuário</th>
                <th style={{ padding: "10px" }}>Ação</th>
                <th style={{ padding: "10px" }}>Recurso</th>
                <th style={{ padding: "10px" }}>Nome</th>
                <th style={{ padding: "10px" }}>Detalhes</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid #393e46", color: "#eeeeee" }}>
                  <td style={{ padding: "10px", fontSize: "13px", opacity: 0.7 }}>{log.timestamp}</td>
                  <td style={{ padding: "10px" }}>{log.user}</td>
                  <td style={{ padding: "10px" }}>{LABELS[log.action] ?? log.action}</td>
                  <td style={{ padding: "10px", opacity: 0.7 }}>{log.resource_type || "—"}</td>
                  <td style={{ padding: "10px" }}>{log.resource_name || "—"}</td>
                  <td style={{ padding: "10px", fontSize: "13px", opacity: 0.7 }}>{log.details || "—"}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "30px", textAlign: "center", color: "#eeeeee", opacity: 0.4 }}>
                    Nenhuma ação registrada ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}