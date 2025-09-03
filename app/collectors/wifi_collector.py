import io
import base64
import datetime as dt
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from flask import current_app
from .base_collector import BaseCollector


class WiFiCollector(BaseCollector):
    """
    Módulo Wi‑Fi (Contagem de Clientes por AP/SSID)
    - Usa perfis/detecção e trends com fallback para history (unsigned) por período.
    - Mantém gráficos e tabelas atuais.
    """

    def _prepare_kpi_cards(self, df, capacity_per_ap):
        if df.empty:
            return []

        pico_global = int(df["value_avg"].max()) if not df.empty else 0
        p95_global = int(df["value_avg"].quantile(0.95)) if not df.empty else 0
        total_aps = df["hostid"].nunique()

        # Ícones SVG para cada KPI
        icons = {
            'pico': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M0 0h1v15h15v1H0V0zm10 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V4.9l-3.613 4.417a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61L13.445 4H10.5a.5.5 0 0 1-.5-.5z"/></svg>',
            'percentil': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" viewBox="0 0 16 16"><path d="M13.442 2.558a.625.625 0 0 1 0 .884l-10 10a.625.625 0 1 1-.884-.884l10-10a.625.625 0 0 1 .884 0zM4.5 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zm7 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"/></svg>',
            'aps': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" viewBox="0 0 16 16"><path d="M5.525 0.16A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .475.16l.644.7a.5.5 0 0 1 .105.274l.25 1.154a.5.5 0 0 1-.458.614l-1.08.216a.5.5 0 0 1-.613-.458l-.25-1.154a.5.5 0 0 1 .106-.274L6 0zm4 0 1.354.84A.5.5 0 0 1 10.25 1l.25 1.154a.5.5 0 0 1-.613.458L8.8 2.4a.5.5 0 0 1-.458-.614l.25-1.154a.5.5 0 0 1 .106-.274L10 0zM.5 3A.5.5 0 0 1 1 2.5h14a.5.5 0 0 1 0 1H1a.5.5 0 0 1-.5-.5zM2.5 5A.5.5 0 0 1 3 4.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zM2 10.5a.5.5 0 0 1 .5-.5h11a.5.5 0 0 1 0 1h-11a.5.5 0 0 1-.5-.5zM1.5 13a.5.5 0 0 1 .5-.5h12a.5.5 0 0 1 0 1h-12a.5.5 0 0 1-.5-.5z"/></svg>',
            'capacity': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" viewBox="0 0 16 16"><path d="M0 11.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1-.5-.5v-2zm4-3a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1-.5-.5v-5zm4-3a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1-.5-.5v-8zm4-3a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 .5.5v11a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1-.5-.5v-11z"/></svg>'
        }

        kpis_list = [
            {
                "label": "Pico Global de Clientes",
                "value": pico_global,
                "sublabel": "Máximo de clientes simultâneos em um único AP",
                "status": "critico" if pico_global > (capacity_per_ap * 0.8) else "ok",
                "icon": icons['pico']
            },
            {
                "label": "Percentil 95 Global",
                "value": p95_global,
                "sublabel": "Valor que o uso ficou abaixo em 95% do tempo",
                "status": "ok",
                "icon": icons['percentil']
            },
            {
                "label": "Total de APs Analisados",
                "value": total_aps,
                "sublabel": "Quantidade de pontos de acesso com dados",
                "status": "info",
                "icon": icons['aps']
            },
            {
                "label": "Capacidade por AP",
                "value": int(capacity_per_ap),
                "sublabel": "Referência para cálculo de saturação",
                "status": "info",
                "icon": icons['capacity']
            }
        ]
        return kpis_list

    def _get_wifi_dataframe(self, all_hosts, period):
        self._update_status("Coletando dados Wi-Fi...")
        host_ids = [h["hostid"] for h in all_hosts]
        host_map = {h["hostid"]: h["nome_visivel"] for h in all_hosts}

        wifi_keys = self._resolve_wifi_keys()
        items = []
        for key in wifi_keys:
            items.extend(self.generator.get_items(host_ids, key, search_by_key=True))
        
        if not items:
            return pd.DataFrame(), pd.DataFrame(), "Nenhum item Wi-Fi encontrado."

        key_prio = {k: i for i, k in enumerate(wifi_keys)}
        best_per_host = {}
        for it in items:
            hid, key = it.get("hostid"), it.get("key_", "")
            pr = min([key_prio[k] for k in key_prio if k in key] or [999])
            cur = best_per_host.get(hid)
            if (not cur) or pr < cur.get("_prio", 999):
                it2 = dict(it)
                it2["_prio"] = pr
                best_per_host[hid] = it2
        
        items = list(best_per_host.values())
        if not items:
            return pd.DataFrame(), pd.DataFrame(), "Nenhum item Wi-Fi elegível por host."

        item_ids = [it["itemid"] for it in items]
        trends = self.generator.get_trends(item_ids, period)
        if not trends or not isinstance(trends, list) or len(trends) == 0:
            points = self.generator.get_history_points(item_ids, period['start'], period['end'], history_value_type=3)
            if not points:
                return pd.DataFrame(), pd.DataFrame(), "Sem dados de Wi-Fi para o período."
            df = pd.DataFrame(points)
            df.rename(columns={"value": "value_avg"}, inplace=True)
        else:
            df = pd.DataFrame(trends)

        for c in ["clock", "value_avg"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["clock", "value_avg"])
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), "Dados inválidos."

        item_to_host = {it["itemid"]: it["hostid"] for it in items}
        df["hostid"] = df["itemid"].map(item_to_host)
        df["host"] = df["hostid"].map(host_map)
        df["datetime"] = df["clock"].apply(lambda x: dt.datetime.fromtimestamp(int(x)))
        df["date"] = df["datetime"].dt.date
        
        daily_ap = df.groupby(["host", "date"])["value_avg"].max().reset_index()
        
        return df, daily_ap, None

    def collect(self, all_hosts, period, previous_month_data=None):
        opts = (self.module_config or {}).get("custom_options", {}) or {}
        chart_mode = str(opts.get("chart", "bar")).lower()
        table_mode = str(opts.get("table", "both")).lower()
        heatmap_mode = str(opts.get("heatmap", "global")).lower()
        capacity = float(opts.get("capacity_per_ap", 50))
        max_charts = int(opts.get("max_charts", 6))

        df, daily_ap, error_msg = self._get_wifi_dataframe(all_hosts, period)

        if error_msg:
            return self.render("wifi", {"error": error_msg})

        # KPIs
        kpi_cards_data = self._prepare_kpi_cards(df, capacity)

        # Agregações
        summary_rows = []
        detailed_blocks = []

        if table_mode in ("summary", "both"):
            total_current = daily_ap.groupby("host")["value_avg"].sum().reset_index()
            
            if previous_month_data is not None and not previous_month_data.empty:
                # Renomeia a coluna do mês anterior para o merge
                prev_data_renamed = previous_month_data.rename(columns={'value_avg': 'total_prev'})
                total_current = pd.merge(total_current, prev_data_renamed, on="host", how="left")
                total_current['total_prev'] = total_current['total_prev'].fillna(0)
            else:
                total_current['total_prev'] = 0

            for _, r in total_current.iterrows():
                summary_rows.append({
                    "host": r["host"],
                    "ap": "-",
                    "total_current": int(r["value_avg"]),
                    "total_prev": int(r["total_prev"])
                })

        if table_mode in ("detailed", "both"):
            for host, part in daily_ap.groupby("host"):
                rows = [{"date": str(d), "max_daily": int(v)} for d, v in zip(part["date"], part["value_avg"])]
                detailed_blocks.append({"host": host, "ap": "AP", "rows": rows})

        # Gráficos
        charts_ap = []
        line_chart = None

        if chart_mode in ("bar", "both"):
            top_hosts = (daily_ap.groupby("host")["value_avg"].sum()
                                   .sort_values(ascending=False)
                                   .head(max_charts).index)
            for host in top_hosts:
                part = daily_ap[daily_ap["host"] == host]
                charts_ap.append(self._render_bar_chart(part, f"{host} – Máximo diário"))

        if chart_mode in ("line", "both"):
            global_daily = daily_ap.groupby("date")["value_avg"].sum().reset_index()
            line_chart = self._render_line_chart(global_daily, "Clientes Wi‑Fi – soma dos máximos diários")

        # Heatmaps
        heatmap_global = None
        heatmap_per_ap = []
        if heatmap_mode in ("global", "both"):
            heatmap_global = self._render_heatmap_global(df)
        if heatmap_mode in ("per_ap", "both"):
            for host, part in df.groupby("host"):
                heatmap_per_ap.append(self._render_heatmap_single(part, f"{host}"))

        data = {
            "error": None,
            "opts": opts,
            "kpis_data": kpi_cards_data,
            "charts_ap": charts_ap,
            "line_chart": line_chart,
            "summary_rows": summary_rows,
            "detailed_blocks": detailed_blocks,
            "heatmap_global": heatmap_global,
            "heatmap_per_ap": heatmap_per_ap,
            "show_table_summary": table_mode in ("summary", "both"),
            "show_table_detailed": table_mode in ("detailed", "both")
        }
        return self.render("wifi", data)

    # ---------------- Helpers ----------------
    def _resolve_wifi_keys(self):
        try:
            from app.models import MetricKeyProfile
            profs = MetricKeyProfile.query.filter_by(metric_type="wifi_clients", is_active=True).all()
            return [p.key_string for p in profs] if profs else ["clientcountnumber"]
        except Exception as e:
            current_app.logger.warning(f"[WiFi] Falha ao buscar keys: {e}")
            return ["clientcountnumber"]

    def _fig_to_img(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _render_bar_chart(self, df, title):
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.bar(df["date"].astype(str), df["value_avg"])
        ax.set_title(title)
        ax.set_ylabel("Máximo diário")
        ax.set_xlabel("Dia")
        ax.grid(axis="y", linestyle="--", alpha=0.3)

        # Melhorias no eixo X para evitar sobreposição
        plt.xticks(rotation=45, ha='right')
        for i, label in enumerate(ax.get_xticklabels()):
            if i % 2 != 0:
                label.set_visible(False)
        
        return self._fig_to_img(fig)

    def _render_line_chart(self, df, title):
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(df["date"].astype(str), df["value_avg"])
        ax.set_title(title)
        ax.set_ylabel("Clientes")
        ax.set_xlabel("Dia")
        ax.grid(True, linestyle="--", alpha=0.3)

        # Melhorias no eixo X para evitar sobreposição
        plt.xticks(rotation=45, ha='right')
        for i, label in enumerate(ax.get_xticklabels()):
            if i % 2 != 0:
                label.set_visible(False)

        return self._fig_to_img(fig)

    def _render_heatmap_global(self, df):
        df = df.copy()
        df["hour"] = df["datetime"].dt.hour
        mat = df.groupby("hour")["value_avg"].mean().reindex(range(24), fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 1.6))
        ax.imshow([mat.values], aspect="auto")
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{h:02d}h" for h in range(0, 24, 2)])
        ax.set_yticks([])
        ax.set_title("Heatmap Global – média por hora")
        return self._fig_to_img(fig)

    def _render_heatmap_single(self, df_ap, title):
        df_ap = df_ap.copy()
        df_ap["hour"] = df_ap["datetime"].dt.hour
        mat = df_ap.groupby("hour")["value_avg"].mean().reindex(range(24), fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 1.6))
        ax.imshow([mat.values], aspect="auto")
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{h:02d}h" for h in range(0, 24, 2)])
        ax.set_yticks([])
        ax.set_title(f"Heatmap – {title}")
        return self._fig_to_img(fig)

