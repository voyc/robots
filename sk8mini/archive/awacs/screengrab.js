!function(e) {
    var t = {};
    function r(n) {
        if (t[n])
            return t[n].exports;
        var o = t[n] = {
            i: n,
            l: !1,
            exports: {}
        };
        return e[n].call(o.exports, o, o.exports, r),
        o.l = !0,
        o.exports
    }
    r.m = e,
    r.c = t,
    r.d = function(e, t, n) {
        r.o(e, t) || Object.defineProperty(e, t, {
            enumerable: !0,
            get: n
        })
    }
    ,
    r.r = function(e) {
        "undefined" != typeof Symbol && Symbol.toStringTag && Object.defineProperty(e, Symbol.toStringTag, {
            value: "Module"
        }),
        Object.defineProperty(e, "__esModule", {
            value: !0
        })
    }
    ,
    r.t = function(e, t) {
        if (1 & t && (e = r(e)),
        8 & t)
            return e;
        if (4 & t && "object" == typeof e && e && e.__esModule)
            return e;
        var n = Object.create(null);
        if (r.r(n),
        Object.defineProperty(n, "default", {
            enumerable: !0,
            value: e
        }),
        2 & t && "string" != typeof e)
            for (var o in e)
                r.d(n, o, function(t) {
                    return e[t]
                }
                .bind(null, o));
        return n
    }
    ,
    r.n = function(e) {
        var t = e && e.__esModule ? function() {
            return e.default
        }
        : function() {
            return e
        }
        ;
        return r.d(t, "a", t),
        t
    }
    ,
    r.o = function(e, t) {
        return Object.prototype.hasOwnProperty.call(e, t)
    }
    ,
    r.p = "/out/",
    r(r.s = 461)
}({
    461: function(e, t) {
        let r;
        var n;
        !function(e) {
            e[e.Id = 1] = "Id",
            e[e.Hierarchy = 2] = "Hierarchy",
            e[e.Attributes = 4] = "Attributes",
            e[e.Class = 8] = "Class",
            e[e.NthOfType = 16] = "NthOfType"
        }(n || (n = {}));
        var o;
        !function(e) {
            e[e.Id = 0] = "Id",
            e[e.Class = 1] = "Class",
            e[e.Attributes = 2] = "Attributes",
            e[e.NthOfType = 3] = "NthOfType"
        }(o || (o = {}));
        class s {
            constructor(e) {
                this.rules = [],
                this.tag = "",
                this.elem = e,
                this.hasId = !1
            }
            addRule(e) {
                e.type < o.Id || e.type > o.NthOfType ? console.log("Unexpected selector: " + e.type) : Array.isArray(e.value) && 0 === e.value.length || (e.type === o.Id && (this.hasId = !0),
                this.rules.push(e))
            }
            addTag(e) {
                this.tag = e
            }
            size() {
                return this.rules.length
            }
            toString(e=31) {
                let t = this.tag + "";
                for (const r of this.rules)
                    if ((e & n.Id || r.type !== o.Id) && (e & n.Class || r.type !== o.Class) && (e & n.Attributes || r.type !== o.Attributes) && (e & n.NthOfType || r.type !== o.NthOfType) && !(this.hasId && e & n.Id && r.type === o.Class))
                        switch (r.type) {
                        case o.Id:
                            t += "#" + r.value;
                            break;
                        case o.Class:
                            t += "." + r.value.join(".");
                            break;
                        case o.Attributes:
                            for (const e of r.value) {
                                const r = this.elem.getAttribute(e.attr);
                                let n = "*=";
                                e.attr === r ? n = "=" : e.attr.startsWith(r) && (n = "^="),
                                t += `[${e.attr}${n}"${e.value}"]`
                            }
                            break;
                        case o.NthOfType:
                            t += `:nth-of-type(${r.value})`
                        }
                return t
            }
        }
        const l = e=>{
            var t, r, n, l;
            const i = new s(e);
            e.id.length > 0 && i.addRule({
                type: o.Id,
                value: CSS.escape(e.id)
            }),
            e.classList.length > 0 && i.addRule({
                type: o.Class,
                value: Array.from(e.classList).map(e=>CSS.escape(e))
            });
            const a = CSS.escape(e.localName);
            if (0 === i.size()) {
                const s = [];
                switch (a) {
                case "a":
                    {
                        const r = null === (t = e.getAttribute("href")) || void 0 === t ? void 0 : t.trim().split(/[?#]/)[0];
                        void 0 !== r && r.length > 0 && s.push({
                            attr: "href",
                            value: r
                        });
                        break
                    }
                case "iframe":
                    {
                        const t = null === (r = e.getAttribute("src")) || void 0 === r ? void 0 : r.trim();
                        void 0 !== t && t.length > 0 && s.push({
                            attr: "src",
                            value: t.slice(0, 256)
                        });
                        break
                    }
                case "img":
                    {
                        let t = null === (n = e.getAttribute("src")) || void 0 === n ? void 0 : n.trim();
                        if (void 0 !== t && t.length > 0 && t.startsWith("data:") && (t = t.split(",")[1].slice(0, 256)),
                        void 0 === t || 0 === t.length) {
                            let t = null === (l = e.getAttribute("alt")) || void 0 === l ? void 0 : l.trim();
                            void 0 !== t && t.length > 0 && s.push({
                                attr: "alt",
                                value: t
                            })
                        } else
                            s.push({
                                attr: "src",
                                value: t
                            });
                        break
                    }
                }
                s.length > 0 && i.addRule({
                    type: o.Attributes,
                    value: s
                })
            }
            const u = (e,t)=>{
                if (null !== e)
                    try {
                        let r = e.querySelectorAll(t);
                        return Array.from(r)
                    } catch (e) {}
                return []
            }
            ;
            if ((0 === i.size() || u(e.parentElement, i.toString()).length > 1) && (i.addTag(a),
            u(e.parentElement, i.toString()).length > 1)) {
                let t = 1
                  , r = e.previousElementSibling;
                for (; null !== r; )
                    r.localName === a && t++,
                    r = r.previousElementSibling;
                i.addRule({
                    type: o.NthOfType,
                    value: t
                })
            }
            return i
        }
          , i = e=>{
            "Escape" === e.key && (e.stopPropagation(),
            e.preventDefault(),
            u())
        }
          , a = ()=>{
            p(d)
        }
          , u = ()=>{
            null !== r && document.documentElement.removeChild(r),
            document.removeEventListener("keydown", i, !0),
            document.removeEventListener("resize", a),
            document.removeEventListener("scroll", a)
        }
        ;
        let c = null
          , d = [];
        const p = e=>{
            d = e;
            const t = e.map(e=>(e=>{
                const t = e.getBoundingClientRect();
                return {
                    x: t.left,
                    y: t.top,
                    width: t.right - t.left,
                    height: t.bottom - t.top
                }
            }
            )(e));
            chrome.runtime.sendMessage({
                type: "highlightElements",
                coords: t
            })
        }
        ;
        chrome.runtime.onMessage.addListener((e,t,o)=>{
            switch ("string" == typeof e ? e : e.type) {
            case "elementPickerLaunch":
                (()=>{
                    r = document.createElement("iframe"),
                    r.src = chrome.runtime.getURL("elementPicker.html");
                    const e = ["background: transparent", "border: 0", "border-radius: 0", "box-shadow: none", "display: block", "height: 100%", "left: 0", "margin: 0", "max-height: none", "max-width: none", "opacity: 1", "outline: 0", "padding: 0", "pointer-events: auto", "position: fixed", "top: 0", "visibility: visible", "width: 100%", "z-index: 2147483647", ""].join(" !important;");
                    r.style.cssText = e,
                    document.documentElement.appendChild(r),
                    document.addEventListener("keydown", i, !0),
                    document.addEventListener("resize", a),
                    document.addEventListener("scroll", a)
                }
                )();
                break;
            case "quitElementPicker":
                u();
                break;
            case "elementPickerHoverCoordsChanged":
                {
                    const {coords: t} = e
                      , n = ((e,t)=>{
                        if (!r)
                            return null;
                        r.style.setProperty("pointer-events", "none", "important");
                        const n = document.elementFromPoint(e, t);
                        return r.style.setProperty("pointer-events", "auto", "important"),
                        n
                    }
                    )(t.x, t.y);
                    null !== n && n instanceof HTMLElement && n !== c && (p([n]),
                    c = n);
                    break
                }
            case "elementPickerUserSelectedTarget":
                {
                    const {specificity: t} = e;
                    if (null !== c && c instanceof HTMLElement) {
                        const e = ((e,t)=>{
                            if (null === c)
                                return "";
                            let r = e;
                            const o = []
                              , s = [13, 29, 11, 19, 31][t];
                            if (s & n.Hierarchy)
                                for (; null !== r && r !== document.body; )
                                    o.push(l(r)),
                                    r = r.parentElement;
                            else
                                o.push(l(e));
                            let i = 0;
                            for (; i < o.length; i++) {
                                const e = o[i];
                                if (s & n.Id && e.hasId || 1 === document.querySelectorAll(e.toString(s)).length)
                                    break
                            }
                            return o.slice(0, i + 1).reverse().map(e=>e.toString(s)).join(" > ")
                        }
                        )(c, t);
                        p(Array.from(document.querySelectorAll(e))),
                        o({
                            isValid: "" !== e,
                            selector: e.trim()
                        })
                    }
                    break
                }
            case "elementPickerUserModifiedRule":
                {
                    const t = e.selector;
                    t.length > 0 && p(Array.from(document.querySelectorAll(t)));
                    break
                }
            case "elementPickerUserCreatedRule":
                chrome.runtime.sendMessage({
                    type: "cosmeticFilterCreate",
                    host: window.location.host,
                    selector: e.selector
                }),
                u()
            }
        }
        )
    }
});

