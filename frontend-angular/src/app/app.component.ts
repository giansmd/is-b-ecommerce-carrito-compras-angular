import { Component, OnInit } from "@angular/core";
import { AuthService, AuthSession } from "./services/auth.service";
import { CartService } from "./services/cart.service";
import { Product, ProductService } from "./services/product.service";

@Component({
  selector: "app-root",
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.css"],
})
export class AppComponent implements OnInit {
  products: Product[] = [];
  cart: Product[] = [];
  session: AuthSession | null = null;
  email = "";
  password = "";
  isLoggedIn = false;
  reportStartDate = "";
  reportEndDate = "";
  isAdmin = false;
  showProductForm = false;
  editingProduct: Product | null = null;
  productForm = {
    name: "",
    description: "",
    price: 0,
    category: "",
    stock: 0,
  };

  constructor(
    private auth: AuthService,
    private productsApi: ProductService,
    private cartApi: CartService,
  ) {}

  ngOnInit() {
    this.loadProducts();
    this.checkSession();
    const today = new Date();
    const end = today.toISOString().slice(0, 10);
    const start = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    this.reportStartDate = start;
    this.reportEndDate = end;
  }

  checkSession() {
    const session = this.auth.session;
    if (session) {
      this.session = session;
      this.isLoggedIn = true;
      this.email = session.email;
      this.isAdmin = session.role === "admin";
    }
  }

  loadProducts() {
    this.productsApi.list().subscribe((res) => (this.products = res));
  }

  login() {
    this.auth.login(this.email, this.password).subscribe({
      next: (session) => {
        this.session = session;
        this.isLoggedIn = true;
        this.isAdmin = session.role === "admin";
        this.loadProducts();
      },
      error: () => alert("Error de login"),
    });
  }

  logout() {
    this.auth.logout();
    this.session = null;
    this.isLoggedIn = false;
    this.isAdmin = false;
    this.cart = [];
  }

  openAddProduct() {
    this.editingProduct = null;
    this.productForm = { name: "", description: "", price: 0, category: "", stock: 0 };
    this.showProductForm = true;
  }

  openEditProduct(product: Product) {
    this.editingProduct = product;
    this.productForm = {
      name: product.name,
      description: product.description || "",
      price: Number(product.price),
      category: product.category || "",
      stock: product.stock,
    };
    this.showProductForm = true;
  }

  saveProduct() {
    if (this.editingProduct) {
      this.productsApi.update(this.editingProduct.id, this.productForm).subscribe({
        next: () => {
          this.loadProducts();
          this.showProductForm = false;
          alert("Producto actualizado");
        },
        error: () => alert("Error al actualizar producto"),
      });
    } else {
      this.productsApi.create(this.productForm).subscribe({
        next: () => {
          this.loadProducts();
          this.showProductForm = false;
          alert("Producto creado");
        },
        error: () => alert("Error al crear producto"),
      });
    }
  }

  deleteProduct(id: number) {
    if (confirm("¿Estás seguro de eliminar este producto?")) {
      this.productsApi.delete(id).subscribe({
        next: () => {
          this.loadProducts();
          alert("Producto eliminado");
        },
        error: () => alert("Error al eliminar producto"),
      });
    }
  }

  addToCart(product: Product) {
    if (!this.isLoggedIn) {
      alert("Debes iniciar sesión");
      return;
    }
    this.cartApi.addToCart(product.id, 1).subscribe({
      next: () => {
        this.cart.push(product);
        alert("Producto agregado al carrito");
      },
      error: () => alert("No se pudo agregar al carrito"),
    });
  }

  checkout() {
    this.cartApi.checkout().subscribe({
      next: (res) => {
        this.cart = [];
        alert(`Compra realizada. Pedido #${res.order_id}. Total: ${res.total}`);
      },
      error: () => alert("No se pudo procesar el checkout"),
    });
  }

  generateOperationalReport() {
    this.cartApi.generateOperationalReport(this.reportStartDate, this.reportEndDate).subscribe({
      next: (res) => this.openPdf(res.pdf_url),
      error: () => alert("No se pudo generar el reporte operacional"),
    });
  }

  generateManagementReport() {
    this.cartApi.generateManagementReport().subscribe({
      next: (res) => this.openPdf(res.pdf_url),
      error: () => alert("No se pudo generar el reporte gerencial"),
    });
  }

  private openPdf(pdfUrl: string) {
    const absolute = `${this.auth.backendUrl}${pdfUrl}`;
    window.open(absolute, "_blank");
  }
}
