import { Component, OnInit } from "@angular/core";
import { HttpClient } from "@angular/common/http";

@Component({
  selector: "app-root",
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.css"],
})
export class AppComponent implements OnInit {
  backendUrl = (window as any).env?.BACKEND_URL || "http://localhost:8000";
  products: any[] = [];
  cart: any[] = [];
  user: any = null;
  email = "";
  password = "";
  isLoggedIn = false;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadProducts();
    const savedUser = localStorage.getItem("user");
    if (savedUser) {
      this.user = JSON.parse(savedUser);
      this.isLoggedIn = true;
    }
  }

  loadProducts() {
    this.http.get(`${this.backendUrl}/api/products`).subscribe((res: any) => {
      this.products = res;
    });
  }

  login() {
    this.http
      .post(`${this.backendUrl}/api/auth/login`, {
        email: this.email,
        password: this.password,
      })
      .subscribe(
        (res: any) => {
          this.user = res;
          this.isLoggedIn = true;
          localStorage.setItem("user", JSON.stringify(res));
        },
        (err) => {
          alert("Error de login");
        },
      );
  }

  logout() {
    this.user = null;
    this.isLoggedIn = false;
    localStorage.removeItem("user");
  }

  addToCart(product: any) {
    if (!this.isLoggedIn) {
      alert("Debes iniciar sesión");
      return;
    }
    // Simulación local del carrito para simplificar el frontend angular
    this.cart.push(product);
    alert("Producto añadido al carrito (local)");
  }

  checkout() {
    alert("Funcionalidad de checkout pendiente de integrar con backend real");
  }
}
