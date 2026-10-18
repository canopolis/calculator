# -*- coding: utf-8 -*-
"""
Calculadora Canopolis v2.5
- MRC / M- / M+ (memoria)
- CE (borra la entrada actual) / ON-C (borra todo)
- %, raiz cuadrada, +/-
- Orden de operaciones (PEMDAS) con paréntesis
- Teclado físico completo, sin depender del foco de ningún botón
"""
import tkinter as tk
import tkinter.font as tkfont
import ast
import operator
import os
import sys
import math
from decimal import Decimal

# ---------- Motor de evaluación seguro ----------
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def evaluar(expr: str) -> float:
    nodo = ast.parse(expr, mode="eval")

    def _ev(n):
        if isinstance(n, ast.Expression):
            return _ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_ev(n.left), _ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](_ev(n.operand))
        raise ValueError("Expresión no válida")

    return _ev(nodo)


MAX_DIGITOS = 16  # límite al ESCRIBIR un número


def _a_texto(num) -> str:
    """Número -> texto con su valor REAL completo, sin comas ni notación científica."""
    if isinstance(num, float):
        if not math.isfinite(num):
            raise ValueError("Número fuera de rango")
        # 15 cifras significativas: evita basura de coma flotante (0.1+0.2 = 0.3)
        r = format(Decimal(f"{num:.15g}"), "f")
        if "." in r:
            r = r.rstrip("0").rstrip(".")
        return "0" if r in ("-0", "") else r
    return str(num)


def _cientifica(num: float, digitos: int) -> str:
    m, e = f"{num:.{digitos}e}".split("e")
    if "." in m:
        m = m.rstrip("0").rstrip(".")
    return f"{m}e{int(e):+d}"


def formatear(num: float) -> str:
    return formatear_token(_a_texto(num))


def formatear_token(tok: str) -> str:
    if tok in ("", "-"):
        return tok
    if "e" in tok:
        return tok
    neg = tok.startswith("-")
    t = tok[1:] if neg else tok
    if "." in t:
        ent, dec = t.split(".", 1)
        ent_f = f"{int(ent):,}" if ent else "0"
        res = f"{ent_f}.{dec}"
    else:
        res = f"{int(t):,}" if t else ""
    return ("-" + res) if neg else res


class Calculadora(tk.Tk):
    def __init__(self):
        super().__init__()
        # Medidas siempre a escala 100 %, igual que la captura de referencia
        self.tk.call("tk", "scaling", 96 / 72)
        self.title("Calculadora Canopolis")
        self.resizable(False, False)
        # Tamaño fijo al abrir (como la calculadora clásica de Windows)
        self.geometry("264x486")
        for c in range(4):
            self.columnconfigure(c, weight=1, uniform="col")
        for r in range(2, 9):
            self.rowconfigure(r, weight=1, uniform="fila")
        self.configure(bg="#c9c9d0")

        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            self.iconbitmap(os.path.join(base, "icono2.ico"))
        except Exception:
            pass

        self.tokens = [""]
        self.resultado_mostrado = False
        self.memoria = 0.0
        self._ultimo_boton = None

        # Pantalla de tamaño FIJO: el ancho lo marcan los botones, no el número.
        # Si la cifra no cabe, la letra se reduce automáticamente.
        self._fuente_max = 22
        self._fuente_min = 14
        self._fuente_pantalla = tkfont.Font(family="Consolas", size=self._fuente_max, weight="bold")
        alto_fijo = self._fuente_pantalla.metrics("linespace") + 2 * 8 + 2 * 4
        self.marco_pantalla = tk.Frame(self, height=alto_fijo, width=1, bg="#c9c9d0")
        self.marco_pantalla.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=6, pady=(6, 2))
        self.marco_pantalla.grid_propagate(False)
        self.marco_pantalla.pack_propagate(False)
        self.pantalla = tk.Label(
            self.marco_pantalla, text="0", anchor="e", bg="#dfe6dd", fg="#1a1a1a",
            font=self._fuente_pantalla, padx=8, pady=8, relief="sunken", bd=4, width=1
        )
        self.pantalla.pack(fill="both", expand=True)
        self._texto_pantalla = "0"
        self.pantalla.bind("<Configure>", lambda e: self._ajustar_pantalla())

        self.indicador_mem = tk.Label(
            self, text="", bg="#c9c9d0", fg="#2a2a2a", font=("Segoe UI", 9, "bold")
        )
        self.indicador_mem.grid(row=1, column=0, sticky="w", padx=14)

        botones = [
            ("MRC", 2, 0, "#2b3a67"), ("M-", 2, 1, "#2b3a67"), ("M+", 2, 2, "#2b3a67"), ("CE", 2, 3, "#3a4a80"),
            ("7", 3, 0, "#5a5a66"), ("8", 3, 1, "#5a5a66"), ("9", 3, 2, "#5a5a66"), ("%", 3, 3, "#2b3a67"),
            ("4", 4, 0, "#5a5a66"), ("5", 4, 1, "#5a5a66"), ("6", 4, 2, "#5a5a66"), ("√", 4, 3, "#2b3a67"),
            ("1", 5, 0, "#5a5a66"), ("2", 5, 1, "#5a5a66"), ("3", 5, 2, "#5a5a66"), ("×", 5, 3, "#2b3a67"),
            ("0", 6, 0, "#5a5a66"), (".", 6, 1, "#5a5a66"), ("+/-", 6, 2, "#5a5a66"), ("÷", 6, 3, "#2b3a67"),
        ]
        for (txt, r, c, color) in botones:
            b = tk.Button(
                self, text=txt, width=1, height=1, bg=color, fg="white", takefocus=0,
                font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
                activebackground="#1c274a", activeforeground="white",
                command=lambda t=txt: self.pulsar(t)
            )
            b.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")

        # Fila de +, -  y  = / C separados
        tk.Button(
            self, text="−", width=1, height=1, bg="#2b3a67", fg="white", takefocus=0,
            font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
            activebackground="#1c274a", activeforeground="white",
            command=lambda: self.pulsar("−")
        ).grid(row=7, column=2, padx=3, pady=3, sticky="nsew")

        tk.Button(
            self, text="+", width=1, height=1, bg="#2b3a67", fg="white", takefocus=0,
            font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
            activebackground="#1c274a", activeforeground="white",
            command=lambda: self.pulsar("+")
        ).grid(row=7, column=3, padx=3, pady=3, sticky="nsew")

        tk.Button(
            self, text="(", width=1, height=1, bg="#5a5a66", fg="white", takefocus=0,
            font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
            activebackground="#1c274a", activeforeground="white",
            command=lambda: self.pulsar("(")
        ).grid(row=7, column=0, padx=3, pady=3, sticky="nsew")

        tk.Button(
            self, text=")", width=1, height=1, bg="#5a5a66", fg="white", takefocus=0,
            font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
            activebackground="#1c274a", activeforeground="white",
            command=lambda: self.pulsar(")")
        ).grid(row=7, column=1, padx=3, pady=3, sticky="nsew")

        # Fila: ON/C rojo grande + =
        tk.Button(
            self, text="ON/C", width=1, height=1, bg="#c0392b", fg="white", takefocus=0,
            font=("Segoe UI", 11, "bold"), bd=3, relief="raised",
            activebackground="#8e2418", activeforeground="white",
            command=lambda: self.pulsar("C")
        ).grid(row=8, column=0, columnspan=2, padx=3, pady=(3, 8), sticky="nsew")

        tk.Button(
            self, text="=", width=1, height=1, bg="#c0392b", fg="white", takefocus=0,
            font=("Segoe UI", 14, "bold"), bd=3, relief="raised",
            activebackground="#8e2418", activeforeground="white",
            command=lambda: self.pulsar("=")
        ).grid(row=8, column=2, columnspan=2, padx=3, pady=(3, 8), sticky="nsew")

        # ---- Teclado físico: enlazado a nivel global, sin depender del foco ----
        self.bind_all("<Key>", self.tecla)
        self.bind_all("<Escape>", lambda e: self.pulsar("C"))
        self.bind_all("<Delete>", lambda e: self.pulsar("C"))
        self.bind_all("<BackSpace>", lambda e: self.retroceso())
        self.bind_all("<Return>", lambda e: self.pulsar("="))
        self.bind_all("<KP_Enter>", lambda e: self.pulsar("="))
        self.after(50, self.focus_force)

    # ----- Entrada por teclado -----
    def tecla(self, ev):
        k = ev.char
        keysym = ev.keysym
        if keysym in ("Escape", "Delete", "BackSpace", "Return", "KP_Enter"):
            return  # ya manejadas por bind_all específicos, evita duplicar
        if k.isdigit():
            self.pulsar(k)
        elif k == "+":
            self.pulsar("+")
        elif k == "-":
            self.pulsar("−")
        elif k == "*":
            self.pulsar("×")
        elif k == "/":
            self.pulsar("÷")
        elif k == "(":
            self.pulsar("(")
        elif k == ")":
            self.pulsar(")")
        elif k == ".":
            self.pulsar(".")
        elif k == "%":
            self.pulsar("%")
        elif k in ("c", "C"):
            self.pulsar("C")
        elif k == "=":
            self.pulsar("=")

    # ----- Lógica -----
    def pulsar(self, t):
        anterior = self._ultimo_boton
        self._ultimo_boton = t
        self._ultimo_boton_previo = anterior
        if t == "C":
            self.tokens = [""]
            self.resultado_mostrado = False
        elif t == "CE":
            self.tokens[-1] = ""
            self.resultado_mostrado = False
        elif t == "=":
            self.calcular()
            return
        elif t in ("+", "−", "×", "÷"):
            if self.resultado_mostrado:
                self.resultado_mostrado = False
            if not (self.tokens[-1] == "" and len(self.tokens) > 1 and self.tokens[-2] in "+−×÷"):
                op = t
                if self.tokens[-1] == "" and len(self.tokens) == 1:
                    self.tokens[0] = "0"
                self.tokens.append(op)
                self.tokens.append("")
        elif t in "()":
            if self.resultado_mostrado:
                self.tokens = [""]
                self.resultado_mostrado = False
            if self.tokens[-1] == "":
                self.tokens.insert(len(self.tokens) - 1, t)
            else:
                self.tokens.append(t)
                self.tokens.append("")
        elif t == "+/-":
            tok = self.tokens[-1]
            if tok not in ("", "-"):
                self.tokens[-1] = tok[1:] if tok.startswith("-") else "-" + tok
                self.resultado_mostrado = False
        elif t == "%":
            tok = self.tokens[-1]
            if tok not in ("", "-"):
                valor = float(tok) / 100.0
                if len(self.tokens) >= 3 and self.tokens[-2] in "+−":
                    try:
                        base = evaluar(self._expr_python(self.tokens[:-2]))
                        valor = base * valor
                    except Exception:
                        pass
                self.tokens[-1] = _a_texto(valor)
                self.resultado_mostrado = False
        elif t == "√":
            tok = self.tokens[-1]
            if tok not in ("", "-"):
                try:
                    valor = math.sqrt(float(tok))
                    self.tokens[-1] = _a_texto(valor)
                except ValueError:
                    self._mostrar("Error")
                    return
        elif t == "MRC":
            if self.resultado_mostrado:
                self.tokens = [""]
                self.resultado_mostrado = False
            if self._ultimo_boton_previo == "MRC":
                # Segundo toque consecutivo: borra la memoria
                self.memoria = 0.0
                self.tokens[-1] = "0"
                self._act_indicador()
            else:
                # Primer toque: recupera lo que hay en memoria
                self.tokens[-1] = _a_texto(self.memoria)
        elif t == "M+":
            try:
                self.memoria += evaluar(self._expr_python(self.tokens))
            except Exception:
                pass
            self._act_indicador()
        elif t == "M-":
            try:
                self.memoria -= evaluar(self._expr_python(self.tokens))
            except Exception:
                pass
            self._act_indicador()
        elif t == ".":
            if self.resultado_mostrado:
                self.tokens = [""]
                self.resultado_mostrado = False
            if "." not in self.tokens[-1]:
                self.tokens[-1] = (self.tokens[-1] or "0") + "."
        elif t.isdigit():
            if self.resultado_mostrado:
                self.tokens = [""]
                self.resultado_mostrado = False
            tok = self.tokens[-1]
            if "e" in tok:
                tok = ""
            if sum(ch.isdigit() for ch in tok) < MAX_DIGITOS:
                self.tokens[-1] = tok + t
        self.refrescar()

    def _mostrar(self, texto, num=None):
        self._texto_pantalla = texto
        self._num_pantalla = num
        self._ajustar_pantalla()

    def _ajustar_pantalla(self):
        texto = self._texto_pantalla
        disponible = self.pantalla.winfo_width() - 2 * 8 - 2 * 4 - 4
        if disponible <= 10:
            self.pantalla.config(text=texto)
            return
        tam = self._fuente_max
        self._fuente_pantalla.configure(size=tam)
        while tam > self._fuente_min and self._fuente_pantalla.measure(texto) > disponible:
            tam -= 1
            self._fuente_pantalla.configure(size=tam)
        # Si es un solo número y no cabe ni con la letra mínima: notación científica
        num = getattr(self, "_num_pantalla", None)
        if num is not None and self._fuente_pantalla.measure(texto) > disponible:
            for d in range(15, -1, -1):
                texto = _cientifica(num, d)
                if self._fuente_pantalla.measure(texto) <= disponible:
                    break
        # Si es una operación larga y no cabe, se muestra el final (lo último escrito)
        if self._fuente_pantalla.measure(texto) > disponible:
            while len(texto) > 1 and self._fuente_pantalla.measure("…" + texto) > disponible:
                texto = texto[1:]
            texto = "…" + texto
        self.pantalla.config(text=texto)

    def _act_indicador(self):
        self.indicador_mem.config(text="M" if self.memoria != 0 else "")

    def _expr_python(self, tokens):
        return "".join(
            {"−": "-", "×": "*", "÷": "/"}.get(tok, tok) for tok in tokens
        )

    def retroceso(self):
        if self.tokens[-1]:
            self.tokens[-1] = self.tokens[-1][:-1]
        elif len(self.tokens) > 1:
            self.tokens.pop()
            if self.tokens and self.tokens[-1] in "+−×÷()":
                self.tokens.pop()
                self.tokens.append("")
        self.refrescar()

    def calcular(self):
        expr = self._expr_python(self.tokens).rstrip("+-*/.")
        if not expr:
            return
        try:
            res = evaluar(expr)
            self.tokens = [_a_texto(res)]
            self.resultado_mostrado = True
            self._mostrar(formatear(res), res)
        except ZeroDivisionError:
            self.tokens = [""]
            self._mostrar("No se puede dividir entre 0")
        except Exception:
            self._mostrar("Error")

    def refrescar(self):
        partes = []
        for tok in self.tokens:
            if tok in ("+", "−", "×", "÷"):
                partes.append(f" {tok} ")
            elif tok in "()":
                partes.append(tok)
            else:
                partes.append(formatear_token(tok))
        texto = "".join(partes).strip() or "0"
        num = None
        if len(self.tokens) == 1 and self.tokens[0] not in ("", "-"):
            try:
                num = float(self.tokens[0])
            except ValueError:
                num = None
        self._mostrar(texto, num)


def _activar_dpi():
    # Evita que Windows agrande la ventana con el escalado de pantalla (125 %, 150 %...)
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if __name__ == "__main__":
    _activar_dpi()
    Calculadora().mainloop()
